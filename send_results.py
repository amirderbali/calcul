import xmlrpc.client
import xml.etree.ElementTree as ET
import os
import sys

# ============================================================
# === CONFIGURATION ODOO ===
# ============================================================
ODOO_URL      = "http://localhost:8069"  
ODOO_DB       = "test_management"
ODOO_USER     = "admin@odoo.com"
# Utilise ton mot de passe en clair ou ta clé API mise à jour
ODOO_PASSWORD  = "bb8701747e7bd392f150ae4118d4ca33780ecac6"
# ============================================================
# CONNEXION ODOO
# ============================================================
def connect_odoo():
    print(f" Tentative de connexion à {ODOO_URL}...")
    try:
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        
        if not uid:
            print(f" Erreur : Identifiants incorrects (DB: {ODOO_DB}, User: {ODOO_USER})")
            raise Exception("Authentification Odoo échouée !")
            
        print(f" Connecté à Odoo (uid={uid})")
        models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
        return uid, models
        
    except Exception as e:
        print(f" Erreur lors de la connexion : {str(e)}")
        raise
        
# ============================================================
# PARSER LE XML (PYTEST)
# ============================================================
def parse_junit_xml(xml_file="results.xml"):
    if not os.path.exists(xml_file):
        raise FileNotFoundError(f"Le fichier {xml_file} est introuvable !")
        
    tree = ET.parse(xml_file)
    root = tree.getroot()
    results = []

    for testcase in root.iter('testcase'):
        name = testcase.attrib.get("name", "unknown")
        result = {
            "name": name,
            "status": "pass", 
            "message": ""
        }

        failure = testcase.find('failure')
        error = testcase.find('error')
        
        if failure is not None or error is not None:
            element = failure if failure is not None else error
            result["status"] = "fail" 
            msg = element.attrib.get('message') or element.text or "Assertion Error"
            result["message"] = msg.split('\n')[0] 

        results.append(result)
    return results

# ============================================================
# ENVOYER LES RÉSULTATS (VERSION DYNAMIQUE)
# ============================================================
def send_to_odoo(uid, models, results):
    # CHANGEMENT ICI : On vérifie les deux noms de variables possibles
    run_id_str = os.environ.get("ODOO_TEST_RUN_ID") or os.environ.get("ODOO_ID")
    
    if not run_id_str:
        print(" Erreur : ODOO_ID ou ODOO_TEST_RUN_ID est introuvable dans l'environnement.")
        return

    try:
        run_id = int(run_id_str)
    except ValueError:
        print(f" Erreur : L'ID fourni n'est pas un nombre valide : {run_id_str}")
        return

    build_number = os.environ.get("BUILD_NUMBER", "local")
    
    # Calcul du résultat global
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

    # 2. Nettoyer les anciennes étapes pour ce Run
    existing_steps = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'test.run.step', 'search',
        [[['test_run_id', '=', run_id]]]
    )
    if existing_steps:
        models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'test.run.step', 'unlink', [existing_steps])

    # 3. Créer les nouvelles étapes de résultat
    for r in results:
        models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'test.run.step', 'create',
            [{
                'test_run_id':     run_id,
                'description':     f"{r['name']}",
                'expected_result': "Success",
                'actual_result':   r["message"] if r["message"] else "OK",
                'state':           r["status"], 
            }]
        )

    # 4. Finaliser le Test Run dans Odoo
    try:
        models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'test.run', 'action_done', [[run_id]])
        print(f" Test Run {run_id} passé à l'état Terminé.")
    except Exception as e:
        print(f" Note : L'appel à action_done a échoué (Peut-être déjà terminé) : {e}")

    print(f" Résultat synchronisé : {global_result.upper()}")

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    try:
        uid, models = connect_odoo()
        results     = parse_junit_xml("results.xml")
        send_to_odoo(uid, models, results)
    except Exception as e:
        print(f" Erreur critique : {e}")
        sys.exit(1)