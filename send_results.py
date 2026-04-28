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
        result = {
            "name":      testcase.attrib.get("name", "unknown"),
            "classname": testcase.attrib.get("classname", ""),
            "duration":  float(testcase.attrib.get("time", 0)),
            "status":    "pass",
            "message":   ""
        }
        if testcase.find('failure') is not None:
            result["status"]  = "fail"
            result["message"] = testcase.find('failure').text or ""
        elif testcase.find('error') is not None:
            result["status"]  = "fail"
            result["message"] = testcase.find('error').text or ""

        results.append(result)
    return results

# ============================================================
# ENVOYER LES RÉSULTATS
# ============================================================
def send_to_odoo(uid, models, results):
    build_number = os.environ.get("BUILD_NUMBER", "local")
    job_name     = os.environ.get("JOB_NAME", "calcul")

    global_result = "fail" if any(r["status"] == "fail" for r in results) else "pass"

    # 1. Projet
    project_id = get_or_create_project(uid, models, job_name)

    # 2. Test Case
    test_case_id = get_or_create_test_case(uid, models, project_id, job_name)

    # 3. Créer le Test Run
    run_id = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'test.run', 'create',
        [{
            'name':         f"Build #{build_number}",
            'test_case_id': test_case_id,
            'description':  f"Jenkins Build #{build_number}",
            'state':        'draft',
            'result':       global_result,
        }]
    )

    # 4. Action Start (si la méthode existe dans votre module Odoo)
    try:
        models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'test.run', 'action_start', [[run_id]])
    except:
        pass 

    # 5. Créer les étapes
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

    # 6. Action Done
    try:
        models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'test.run', 'action_done', [[run_id]])
    except:
        pass

    print(f" Résultat envoyé Build #{build_number} : {global_result.upper()}")

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
