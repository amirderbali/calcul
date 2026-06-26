import xmlrpc.client
import xml.etree.ElementTree as ET
import os
import sys

ODOO_URL      = "http://localhost:8069"
ODOO_DB       = "test_management"
ODOO_USER     = "admin@odoo.com"
ODOO_PASSWORD = "a299a3d73bd6369bbf3da376b4b322bc7694ce7c"


def connect_odoo():
    print(f" Tentative de connexion à {ODOO_URL}...")
    try:
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        if not uid:
            raise Exception("Authentification Odoo échouée !")
        print(f" Connecté à Odoo (uid={uid})")
        models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
        return uid, models
    except Exception as e:
        print(f" Erreur lors de la connexion : {str(e)}")
        raise


def _extract_description_and_steps(system_out_text):
    """
    A partir du <system-out> capturé par pytest :
      - la ligne 'DESCRIPTION::...' devient la description lisible de l'étape
      - les lignes 'Étape N : ...' deviennent les détails (résultat réel)
    """
    title = ""
    steps = []
    for line in (system_out_text or "").splitlines():
        s = line.strip()
        if s.startswith("DESCRIPTION::"):
            title = s.split("DESCRIPTION::", 1)[1].strip()
        elif s.startswith("Étape") or s.startswith("Etape"):
            steps.append(s)
    return title, "\n".join(steps)


def parse_junit_xml(xml_file="results.xml"):
    if not os.path.exists(xml_file):
        raise FileNotFoundError(f"Le fichier {xml_file} est introuvable !")
    tree = ET.parse(xml_file)
    root = tree.getroot()
    results = []
    for testcase in root.iter('testcase'):
        name = testcase.attrib.get("name", "unknown")

        # Détails capturés dans la sortie standard du test
        sysout = testcase.find('system-out')
        sysout_text = sysout.text if sysout is not None else ""
        title, steps_detail = _extract_description_and_steps(sysout_text)

        result = {
            "name": name,                       # clé technique (pour retrouver l'étape)
            "description": title or name,       # description lisible affichée dans Odoo
            "detail": steps_detail,             # les étapes détaillées
            "status": "pass",
            "message": "",
        }

        failure = testcase.find('failure')
        error   = testcase.find('error')
        if failure is not None or error is not None:
            element = failure if failure is not None else error
            result["status"] = "fail"
            msg = element.attrib.get('message') or element.text or "Assertion Error"
            result["message"] = msg.split('\n')[0]

        results.append(result)
    return results


def _build_actual_result(r):
    """Construit le texte du 'Résultat réel' = détails du test + éventuelle erreur."""
    parties = []
    if r["detail"]:
        parties.append(r["detail"])
    if r["status"] == "pass":
        parties.append("==> Résultat : OK")
    else:
        parties.append(f"==> ÉCHEC : {r['message']}")
    return "\n".join(parties) if parties else ("OK" if r["status"] == "pass" else "")


def send_to_odoo(uid, models, results):
    run_id_str = os.environ.get("ODOO_TEST_RUN_ID") or os.environ.get("ODOO_ID")
    if not run_id_str:
        print(" Erreur : ODOO_ID ou ODOO_TEST_RUN_ID introuvable.")
        return
    try:
        run_id = int(run_id_str)
    except ValueError:
        print(f" Erreur : ID invalide : {run_id_str}")
        return

    build_number  = os.environ.get("BUILD_NUMBER", "local")
    global_result = "fail" if any(r["status"] == "fail" for r in results) else "pass"

    print(f" Mise à jour du Test Run ID: {run_id} (Build #{build_number})")

    # 1. Mettre à jour le Test Run
    models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'test.run', 'write',
        [[run_id], {
            'description': f"Mis à jour par Jenkins Build #{build_number}",
            'result': global_result,
        }]
    )

    # 2. Récupérer les étapes existantes (pré-remplies depuis le Cas de Test)
    existing_steps = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'test.run.step', 'search_read',
        [[['test_run_id', '=', run_id]]],
        {'fields': ['id', 'description']}
    )
    step_map = {s['description']: s['id'] for s in existing_steps}

    # 3. Mettre à jour OU créer les étapes
    for r in results:
        actual = _build_actual_result(r)

        # On retrouve l'étape par son nom technique OU par sa description lisible
        # (robuste si le script est relancé sur le même Test Run)
        step_id = step_map.get(r['name']) or step_map.get(r['description'])

        if step_id:
            models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'test.run.step', 'write',
                [[step_id], {
                    'description':   r['description'],   # description lisible
                    'actual_result': actual,             # détails des étapes
                    'state':         r["status"],
                }]
            )
        else:
            models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'test.run.step', 'create',
                [{
                    'test_run_id':     run_id,
                    'description':     r['description'],
                    'expected_result': "Success",
                    'actual_result':   actual,
                    'state':           r["status"],
                }]
            )

        # Auto-resolve bug si succès
        if r["status"] == "pass":
            try:
                models.execute_kw(
                    ODOO_DB, uid, ODOO_PASSWORD,
                    'test.run', 'action_auto_resolve_bugs',
                    [run_id], {'step_description': r['name']}
                )
                print(f" --- Auto-resolve vérifié pour : {r['name']}")
            except Exception as e:
                print(f" --- Erreur auto-resolve pour {r['name']} : {e}")

    # 4. Finaliser le Test Run
    try:
        models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'test.run', 'action_done', [[run_id]])
        print(f" Test Run {run_id} → Terminé.")
    except Exception as e:
        print(f" Note : action_done échoué : {e}")

    print(f" Résultat synchronisé : {global_result.upper()}")


if __name__ == "__main__":
    try:
        uid, models = connect_odoo()
        results     = parse_junit_xml("results.xml")
        send_to_odoo(uid, models, results)
    except Exception as e:
        print(f" Erreur critique : {e}")
        sys.exit(1)