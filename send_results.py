import xmlrpc.client
import xml.etree.ElementTree as ET
import os
import sys

ODOO_URL      = "http://localhost:8069"  
ODOO_DB       = "test_management"
ODOO_USER     = "admin@odoo.com"
ODOO_PASSWORD  = "a299a3d73bd6369bbf3da376b4b322bc7694ce7c"

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

def parse_junit_xml(xml_file="results.xml"):
    if not os.path.exists(xml_file):
        raise FileNotFoundError(f"Le fichier {xml_file} est introuvable !")
    tree = ET.parse(xml_file)
    root = tree.getroot()
    results = []
    for testcase in root.iter('testcase'):
        name = testcase.attrib.get("name", "unknown")
        result = {"name": name, "status": "pass", "message": ""}
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
        if r['name'] in step_map:
            # Étape existante → mise à jour du résultat
            models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'test.run.step', 'write',
                [[step_map[r['name']]], {
                    'actual_result': r["message"] if r["message"] else "OK",
                    'state': r["status"],
                }]
            )
        else:
            # Étape nouvelle → création
            models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'test.run.step', 'create',
                [{
                    'test_run_id':     run_id,
                    'description':     r['name'],
                    'expected_result': "Success",
                    'actual_result':   r["message"] if r["message"] else "OK",
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