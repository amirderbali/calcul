import os
import time
import unittest
from test import addition, soustraction, multiplication
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# ============================================================
#  CONVENTION D'AFFICHAGE
#  - La ligne "DESCRIPTION::xxx"  -> devient la Description de l'etape dans Odoo
#  - Les lignes "Étape N : ..."   -> deviennent les details (Resultat reel)
#  pytest capture ces print() dans <system-out> de results.xml
# ============================================================


# ==========================================
# 1. TESTS UNITAIRES (Back-End)
# ==========================================
class TestCalculator(unittest.TestCase):

    def test_addition(self):
        print("DESCRIPTION::Test unitaire de l'addition (2 + 3 = 5)")
        print("Étape 1 : Appel de la fonction addition(2, 3)")
        resultat = addition(2, 3)
        print(f"Étape 2 : Valeur retournée par la fonction = {resultat}")
        print("Étape 3 : Vérification que le résultat est bien égal à 5")
        self.assertEqual(resultat, 5)

    def test_soustraction(self):
        print("DESCRIPTION::Test unitaire de la soustraction (5 - 3 = 2)")
        print("Étape 1 : Appel de la fonction soustraction(5, 3)")
        resultat = soustraction(5, 3)
        print(f"Étape 2 : Valeur retournée par la fonction = {resultat}")
        print("Étape 3 : Vérification que le résultat est bien égal à 2")
        self.assertEqual(resultat, 2)

    def test_multiplication(self):
        print("DESCRIPTION::Test unitaire de la multiplication (2 x 4 = 8)")
        print("Étape 1 : Appel de la fonction multiplication(2, 4)")
        resultat = multiplication(2, 4)
        print(f"Étape 2 : Valeur retournée par la fonction = {resultat}")
        print("Étape 3 : Vérification que le résultat est bien égal à 8")
        self.assertEqual(resultat, 8)


# ==========================================
# 2. TESTS INTERFACE WEB (Selenium - UI)
# ==========================================
class TestCalculatorUI(unittest.TestCase):

    def setUp(self):
        chrome_options = Options()
        self.is_jenkins = "JENKINS_URL" in os.environ
        if self.is_jenkins:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
        else:
            chrome_options.add_experimental_option("detach", True)

        self.driver = webdriver.Chrome(options=chrome_options)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        chemin_complet = os.path.join(current_dir, 'web.html')
        chemin_normalise = chemin_complet.replace('\\', '/')
        self.base_url = f"file:///{chemin_normalise}"

    def test_selenium_addition_ui(self):
        driver = self.driver
        print("DESCRIPTION::Vérification du fonctionnement de l'opération d'addition (15 + 5 = 20)")

        driver.get(self.base_url)
        print("Étape 1 : Ouverture de la calculatrice")

        driver.find_element(By.ID, "input_a").send_keys("15")
        print("Étape 2 : Saisie du premier nombre (15)")

        driver.find_element(By.ID, "input_b").send_keys("5")
        print("Étape 3 : Saisie du deuxième nombre (5)")

        driver.find_element(By.ID, "bouton_addition").click()
        print("Étape 4 : Clic sur le bouton d'addition (+)")

        if not self.is_jenkins:
            time.sleep(4)

        resultat_affiche = driver.find_element(By.ID, "valeur_resultat").text
        print(f"Étape 5 : Résultat affiché à l'écran = {resultat_affiche} (attendu : 20)")

        self.assertEqual(resultat_affiche, "20")

    def test_selenium_soustraction_ui(self):
        driver = self.driver
        print("DESCRIPTION::Vérification du fonctionnement de l'opération de soustraction (15 - 5 = 10)")

        driver.get(self.base_url)
        print("Étape 1 : Ouverture de la calculatrice")

        driver.find_element(By.ID, "input_a").send_keys("15")
        print("Étape 2 : Saisie du premier nombre (15)")

        driver.find_element(By.ID, "input_b").send_keys("5")
        print("Étape 3 : Saisie du deuxième nombre (5)")

        driver.find_element(By.ID, "bouton_soustraction").click()
        print("Étape 4 : Clic sur le bouton de soustraction (-)")

        if not self.is_jenkins:
            time.sleep(4)

        resultat_affiche = driver.find_element(By.ID, "valeur_resultat").text
        print(f"Étape 5 : Résultat affiché à l'écran = {resultat_affiche} (attendu : 10)")

        self.assertEqual(resultat_affiche, "10")

    def tearDown(self):
        if self.is_jenkins:
            self.driver.quit()


if __name__ == '__main__':
    unittest.main()