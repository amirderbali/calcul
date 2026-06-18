import os
import time
import unittest
from test import addition, soustraction, multiplication
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

# ==========================================
# 1. VOS TESTS UNITAIRES (Back-End)
# ==========================================
class TestCalculator(unittest.TestCase):

    def test_addition(self):
        self.assertEqual(addition(2, 3), 1)

    def test_soustraction(self):
        self.assertEqual(soustraction(5, 3), 2)

    def test_multiplication(self):
        self.assertEqual(multiplication(2, 4), 8)


# ==========================================
# 2. VOS TESTS INTERFACE WEB (Selenium - UI)
# ==========================================
class TestCalculatorUI(unittest.TestCase):

    def setUp(self):
        chrome_options = Options()
        
        # Détection automatique de l'environnement Jenkins
        self.is_jenkins = "JENKINS_URL" in os.environ

        if self.is_jenkins:
            # Configuration stricte et invisible pour le serveur Jenkins
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
        else:
            # Configuration visuelle pour votre PC local (force Chrome à rester visible)
            chrome_options.add_experimental_option("detach", True)

        # Téléchargement automatique et lancement du driver Chrome
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # --- CORRECTION DE LA SYNTAXE POUR PYTHON 3.10 ---
        current_dir = os.path.dirname(os.path.abspath(__file__))
        chemin_complet = os.path.join(current_dir, 'web.html')
        chemin_normalise = chemin_complet.replace('\\', '/') # On fait le replace ici, en dehors de la f-string
        
        self.base_url = f"file:///{chemin_normalise}"
        
    def test_selenium_addition_ui(self):
        driver = self.driver
        driver.get(self.base_url)
        
        # Saisie des valeurs dans les champs de votre interface CSS
        driver.find_element(By.ID, "input_a").send_keys("15")
        driver.find_element(By.ID, "input_b").send_keys("5")
        
        # Clic sur le bouton d'addition (Vert)
        driver.find_element(By.ID, "bouton_addition").click()
        
        # Pause visuelle uniquement sur votre PC pour avoir le temps d'observer
        if not self.is_jenkins:
            time.sleep(4)
        
        # Récupération et vérification du résultat affiché à l'écran
        resultat_affiche = driver.find_element(By.ID, "valeur_resultat").text
        self.assertEqual(resultat_affiche, "20")

    def test_selenium_soustraction_ui(self):
        driver = self.driver
        driver.get(self.base_url)
        
        driver.find_element(By.ID, "input_a").send_keys("15")
        driver.find_element(By.ID, "input_b").send_keys("5")
        
        # Clic sur le bouton de soustraction (Rouge)
        driver.find_element(By.ID, "bouton_soustraction").click()
        
        # Pause visuelle uniquement sur votre PC pour avoir le temps d'observer
        if not self.is_jenkins:
            time.sleep(4)
        
        resultat_affiche = driver.find_element(By.ID, "valeur_resultat").text
        self.assertEqual(resultat_affiche, "10")

    def tearDown(self):
        # On ferme le navigateur TOUJOURS sur Jenkins pour libérer la RAM,
        # mais on le laisse ouvert sur votre PC pour votre vérification visuelle.
        if self.is_jenkins:
            self.driver.quit()

if __name__ == '__main__':
    unittest.main()