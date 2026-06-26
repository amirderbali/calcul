import xmlrpc.client
import xml.etree.ElementTree as ET
import os
import sys

ODOO_URL      = "http://localhost:8069"
ODOO_DB       = "test_management"
ODOO_USER     = "admin@odoo.com"
ODOO_PASSWORD = "a299a3d73bd6369bbf3da376b4b322bc7694ce7c"


def connect_odoo():
    print(f" Tentative de connexion a {ODOO_URL}...")
    try:
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        if not uid:
            raise Exception("Authentification Odoo echouee !")
        print(f" Connecte a Odoo (uid={uid})")
        models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
        return uid, models
    except Exception as e:
        print(f" Erreur lors de la connexion : {str(e)}")
        raise


def _extract_description_and_steps(system_out_text):
    """
    Depuis le <system-out> capture par pytest :
      - 'DESCRIPTION::...'  -> titre lisible du test
      - 'Etape N : ...'     -> LISTE (une entree par etape)
    """
    title = ""
    steps = []
    for line in (system_out_text or "").splitlines():
        s = line.strip()
        if s.startswith("DESCRIPTION::"):
            title = s.split("DESCRIPTION::", 1)[1].strip()
        elif s.startswith("\u00c9tape") or s.startswith("Etape"):
            steps.append(s)
    return title, steps


def parse_junit_xml(xml_file="results.xml"):
    if not os.path.exists(xml_file):
        raise FileNotFoundError(f"Le fichier {xml_file} est introuvable !")
    tree = ET.parse(xml_file)
    root = tree.getroot()
    results = []
    for testcase in root.iter('testcase'):
        name = testcase.attrib.get("name", "unknown")

        sysout = testcase.find('system-out')
        sysout_text = sysout.text if sysout is not None else ""
        title, steps = _extract_description_and_steps(sysout_text)

        result = {
            "name": name,
            "description": title or name,
            "steps": steps,
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

    print(f" Mise a jour du Test Run ID: {run_id} (Build #{build_number})")

    # 1. Mettre a jour le Test Run
    models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'test.run', 'write',
        [[run_id], {
            'description': f"Mis a jour par Jenkins Build #{build_number}",
            'result': global_result,
        }]
    )

    # 2. Vider les etapes existantes (ancien bloc / pre-remplies)
    existing_ids = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'test.run.step', 'search',
        [[['test_run_id', '=', run_id]]]
    )
    if existing_ids:
        models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'test.run.step', 'unlink', [existing_ids]
        )
        print(f" {len(existing_ids)} ancienne(s) etape(s) supprimee(s).")

    # 3. Creer UNE etape par ligne 'Etape N : ...'
    sequence = 10
    for r in results:
        etapes = r["steps"] if r["steps"] else [r["description"]]
        nb = len(etapes)
        test_echoue = (r["status"] == "fail")

        for i, etape in enumerate(etapes):
            derniere = (i == nb - 1)
            if test_echoue and derniere:
                state = "fail"
                actual = f"ECHEC : {r['message']}" if r["message"] else "ECHEC"
            else:
                state = "pass"
                actual = "OK"

            models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'test.run.step', 'create',
                [{
                    'test_run_id':     run_id,
                    'sequence':        sequence,
                    'description':     etape,
                    'expected_result': "Success",
                    'actual_result':   actual,
                    'state':           state,
                }]
            )
            sequence += 10

        print(f" {nb} etape(s) creee(s) pour : {r['description']} [{r['status'].upper()}]")

        if not test_echoue:
            try:
                models.execute_kw(
                    ODOO_DB, uid, ODOO_PASSWORD,
                    'test.run', 'action_auto_resolve_bugs',
                    [run_id], {'step_description': r['name']}
                )
            except Exception as e:
                print(f" --- Note auto-resolve ({r['name']}) : {e}")

    # 4. Finaliser le Test Run
    try:
        models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'test.run', 'action_done', [[run_id]])
        print(f" Test Run {run_id} -> Termine.")
    except Exception as e:
        print(f" Note : action_done echoue : {e}")

    print(f" Resultat synchronise : {global_result.upper()}")


if __name__ == "__main__":
    try:
        uid, models = connect_odoo()
        results     = parse_junit_xml("results.xml")
        send_to_odoo(uid, models, results)
    except Exception as e:
        print(f" Erreur critique : {e}")
        sys.exit(1)