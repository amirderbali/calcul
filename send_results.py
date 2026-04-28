import xmlrpc.client

url = 'http://localhost:8069' # Ton URL Odoo
db = 'test_management'
username = 'admin'
password = 'admin'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Exemple simple pour mettre à jour un état
def update_test_status(test_id, new_state):
    models.execute_kw(db, uid, password, 'test.case', 'write', [[test_id], {
        'state': new_state
    }])

print("Synchronisation avec Odoo terminée.")
