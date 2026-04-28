import xmlrpc.client
import xml.etree.ElementTree as ET
import os

# ============================================================
# === CONFIGURATION ODOO ===
# ============================================================
ODOO_URL      = "http://localhost:8069"  
ODOO_DB       = "test_management"
ODOO_USER      = "admin@odoo.com"
# On essaie de lire une variable d'env, sinon on utilise "admin" en dur
ODOO_PASSWORD  = "eb0b6acea110d3001d1f09ae07b570aa50fe7a51" 

# ============================================================
# CONNEXION ODOO
# ============================================================
def connect_odoo():
    print(f" Tentative de connexion à {ODOO_URL}...")
    try:
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        
        # UTILISATION DES VARIABLES DE CONFIGURATION CI-DESSUS
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
# CHERCHER OU CRÉER LE PROJET ODOO
# ============================================================
def get_or_create_project(uid, models, project_name):
    existing = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'project.project', 'search',
        [[['name', '=', project_name]]]
    )
    if existing:
        print(f" Projet existant : '{project_name}' (id={existing[0]})")
        return existing[0]

    project_id = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'project.project', 'create',
        [{'name': project_name}]
    )
    print(f" Projet créé : '{project_name}' (id={project_id})")
    return project_id

# ============================================================
# CHERCHER OU CRÉER LE TEST CASE
# ============================================================
def get_or_create_test_case(uid, models, project_id, project_name):
    case_name = f"Jenkins - {project_name}"

    existing = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'test.case', 'search',
        [[['name', '=', case_name], ['project_id', '=', project_id]]]
    )
    
    if existing:
        case_id = existing[0]
        models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'test.case', 'write',
            [[case_id], {'state': 'approved'}]
        )
        return case_id

    test_case_id = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'test.case', 'create',
        [{
            'name':       case_name,
            'project_id': project_id,
            'state':      'approved',
            'description': f"Créé par Jenkins pour {project_name}",
        }]
    )
    return test_case_id

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
        # On nettoie le nom du test pour Odoo
        name = testcase.attrib.get("name", "unknown")
        
        result = {
            "name":      name,
            "classname": testcase.attrib.get("classname", ""),
            "duration":  float(testcase.attrib.get("time", 0)),
            "status":    "pass",
            "message":   ""
        }

        # On cherche l'échec (failure) ou l'erreur
        failure_element = testcase.find('failure') or testcase.find('error')
        
        if failure_element is not None:
            result["status"] = "fail"
            # On récupère le texte de l'erreur
            full_error = failure_element.text or "Erreur inconnue"
            
            # --- OPTIMISATION POUR LE BUG ODOO ---
            # On ne prend que la dernière ligne du message d'erreur (ex: AssertionError: 2 != 1)
            # car c'est la plus importante pour le champ 'actual_result' d'Odoo
            lines = [l.strip() for l in full_error.split('\n') if l.strip()]
            if lines:
                result["message"] = lines[-1] 
            else:
                result["message"] = full_error

        results.append(result)
        
    return results

# ============================================================
# ENVOYER LES RÉSULTATS
# ============================================================
# ============================================================
# ENVOYER LES RÉSULTATS (VERSION DYNAMIQUE)
# ============================================================
def send_to_odoo(uid, models, results):
    # 1. Récupérer l'ID du Test Run envoyé par Odoo à Jenkins
    # Jenkins reçoit ODOO_ID en paramètre, il devient une variable d'env pour le script
    run_id_str = os.environ.get("ODOO_ID")
    
    if not run_id_str:
        print(" Erreur : ODOO_ID est introuvable. Le script ne sait pas quel Run mettre à jour.")
        return

    run_id = int(run_id_str)
    build_number = os.environ.get("BUILD_NUMBER", "local")
    
    # Calcul du résultat global
    global_result = "fail" if any(r["status"] == "fail" for r in results) else "pass"

    print(f" Mise à jour du Test Run ID: {run_id} (Build #{build_number})")

    # 2. Mettre à jour le Test Run existant au lieu d'en créer un nouveau
    models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'test.run', 'write',
        [[run_id], {
            'description': f"Mis à jour par Jenkins Build #{build_number}",
            'result': global_result,
        }]
    )

    # 3. Supprimer les étapes existantes si nécessaire (optionnel) 
    # pour éviter les doublons si on relance le même build
    existing_steps = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'test.run.step', 'search',
        [[['test_run_id', '=', run_id]]]
    )
    if existing_steps:
        models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'test.run.step', 'unlink', [existing_steps])

    # 4. Créer les étapes de résultat
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

    # 5. Appeler l'action_done de ton modèle TestRun pour fermer le test
    try:
        models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'test.run', 'action_done', [[run_id]])
        print(f" Test Run {run_id} passé à l'état Terminé.")
    except Exception as e:
        print(f" Erreur lors de l'appel à action_done : {e}")

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
        exit(1)
