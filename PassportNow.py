# -*- coding: utf-8 -*-
"""
Created on Sat Dec 23 06:10:49 2023

@author: hoodog
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from time import time
import datetime
import pandas as pd
import requests
from urllib.parse import quote
import os

def waitTime(timer, interval):
    if time() - timer > interval:
        return True, time()
    return False, timer


def first_connection(driver, link, username, password, periode):
    print(f'starting connection at {datetime.datetime.now().strftime("%H:%M:%S")} ')
    driver.get(link)
    usrnm_form = driver.find_elements(By.ID, "username")
    if len(usrnm_form) > 0:
        usrnm_form[0].send_keys(username)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.NAME, "Submit").click()
        error = driver.find_elements(By.CLASS_NAME, "invalid-feedback")
        error2 = driver.find_elements(By.CLASS_NAME, "text-warning")
        if len(error) > 0 or len(error2) > 0:
            driver.quit()
            return 'Wrong logins'
        else:
            print(f"Successful logins at {datetime.datetime.now().strftime('%H:%M:%S')}           ")
    
    print('connected')
    return scrap_and_format(driver, periode) 
        
        
def scrap_and_format(driver, periode):
    if periode != '':
        periode_boutons = driver.find_elements(By.CLASS_NAME, "btn")
        for p in periode_boutons:
            if periode in p.text:
                bouton_periode = p
                break
        bouton_periode.click()
    appointments = driver.find_elements(By.CLASS_NAME, "nextAvailableAppointments")
    if len(appointments) > 0:
        appointments = appointments[0]
        h4 = appointments.find_elements(By.TAG_NAME, "h4")
        p = appointments.find_elements(By.TAG_NAME, "p")
        uls = appointments.find_elements(By.TAG_NAME, "ul")
        btn = appointments.find_elements(By.CLASS_NAME, "btn")
        noms = [nom.text.replace(' arrondissement','').split('de ')[1] for nom in h4]
        adresses = [adresse.text.split(',')[0] for adresse in p if "PARIS" in adresse.text]
        liens = [link.get_attribute('href') for link in btn]
        lis = [ul.find_elements(By.TAG_NAME, "li") for ul in uls]
        jours = [[jour.text for jour in li] for li in lis]
        liens_heures = [[jour.find_element(By.TAG_NAME,'a').get_attribute('href') for jour in li] for li in lis]
        df = pd.DataFrame({"Nom" : noms, "Adresse" : adresses, "Jour" : jours, "Lien" : liens, "Liens_heures": liens_heures})
        df = df[['Nom','Adresse','Jour','Liens_heures','Lien']]
        df = df.sort_values(by="Nom")
        message = {'Centre_Tolbiac':'Aucun rendez-vous disponible','01_02_03_04':'Aucun rendez-vous disponible',
                '05_06_07_08':'Aucun rendez-vous disponible','09_10_11_12':'Aucun rendez-vous disponible',
                '13_14_15_16':'Aucun rendez-vous disponible','17_18_19_20':'Aucun rendez-vous disponible'}
        for ii, rr in df.iterrows():
            msg = ''
            msg += f'<b>{rr["Nom"]}</b> - {rr["Adresse"]}\n'
            msg += f'<a href="{quote(rr["Lien"])}"> Calendrier des RDV </a>\n'
            for i in range(len(rr["Jour"])):
                msg += f'<a href="{quote(rr["Liens_heures"][i])}"> {rr["Jour"][i]} </a>\n'
            msg += "\n"
            for key in message:
                nom = rr['Nom'].split(' ')[1].lower()
                if len(nom) == 3:
                    nom = nom[:2]
                if nom in key.lower():
                    if 'Aucun rendez-vous disponible' in message[key]:
                        message[key] = ''
                    message[key] += msg
                    ##Mettre en chunck à cause de la limite de canaux telegram
                    
        # driver.quit()
        return message
        
    else:
        return {'Centre_Tolbiac':'Aucun rendez-vous disponible','01_02_03_04':'Aucun rendez-vous disponible',
                '05_06_07_08':'Aucun rendez-vous disponible','09_10_11_12':'Aucun rendez-vous disponible',
                '13_14_15_16':'Aucun rendez-vous disponible','17_18_19_20':'Aucun rendez-vous disponible'}
    

def send_message(msg, TOKEN, chat_id, stored_msg={}):
    if msg != stored_msg:
        for key in msg:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id['chat_id_global']}&text=<b>{key}</b>\n{msg[key]}&parse_mode=HTML"
            requests.get(url).json()
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id[f'chat_id_{key.lower()}']}&text={msg[key]}&parse_mode=HTML"
            requests.get(url).json()
        return msg
    print("Nothing new under the Sun")
    return stored_msg


def main_code(param):
    try :
        TOKEN, chat_ids, periode = param["TOKEN"], param["chat_ids"], param["periode"]
        driver_path, link, interval = param["driver"], param["link"], int(param["interval"])
        username, password = param['email'], param['password']
        driver = webdriver.Chrome(f"{driver_path}")
        msg = first_connection(driver, link, username, password, periode)
        if msg == 'Wrong logins':
            return
        stored_msg = send_message(msg, TOKEN, chat_ids)
        timer = time()
        # ct = 0
        while True:
            doneWaiting, timer = waitTime(timer, interval)
            if doneWaiting:
                print('waited')
                msg = first_connection(driver, link, username, password, periode)
                stored_msg = send_message(msg, TOKEN, chat_ids, stored_msg)
    except KeyboardInterrupt:
        print("quitting: KeyboardInterrupt")
    finally:
        driver.quit()
        print("Driver closed")

print("Démarrage...")
path = os.getcwd()
param = {"TOKEN": '', "chat_ids": {'chat_id_global': '', 'chat_id_centre_tolbiac': '', 'chat_id_01_02_03_04':'',
                                   'chat_id_05_06_07_08':'','chat_id_09_10_11_12':'',
                                   'chat_id_13_14_15_16':'','chat_id_17_18_19_20':''},
         "driver": '', "link": '', "interval": 30,"email":'', "password":'', 'periode':''}
try:
    with open(f"{path}\parameters.txt", encoding="utf-8") as file:
        print('File found')
        for line in file:
            parts = line.strip().split("==")
            if len(parts) == 2:
                variable_name, variable_value = parts
                if 'chat_id' in variable_name:
                    param['chat_ids'][variable_name] = variable_value
                else:
                    param[variable_name] = variable_value
            else:
                print("Vérifier le fichier de paramètrage.")
                raise ValueError("Vérifier le fichier de paramètrage.")
        if param["periode"] not in ['7', '14']:
            raise ValueError("Période ne peut être que 7, 14 ou sans valeur (9 semaines).")
        main_code(param)

except:
     print("Vérifier le fichier de paramètrage.")

