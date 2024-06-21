import pymongo
import csv
from pymongo import MongoClient
import datetime
import time

client = MongoClient('mongodb://mongouser:mongopassword@localhost:27017/')
db = client['meinedatenbank']
file_path = "C:/Users/FHBBook/OneDrive - FH Dortmund/Informatik Studium/Semester 6/Moderne Datenbanken/Projekt/testdaten/dataset.txt"

def load_data():
    #Mapping von alten IDs (aus der CSV-Datei) zu neuen MongoDB ObjectIds
    id_mapping_adressen = {}
    id_mapping_nutzer = {}
    id_mapping_standort = {}
    current_adress_id = 1  # Starte mit der ID 1 und inkrementiere für jede Adresse
    current_nutzer_id = 1  # Starte mit der ID 1 und inkrementiere für jeden Nutzer
    current_standort_id = 1 # Starte mit der ID 1 und inkrementiere für jeden Standort

    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if row[0] == 'Adresse':
                adresse = {
                    "Strasse": row[1],
                    "Hausnummer": row[2],
                    "PLZ": row[3],
                    "Stadt": row[4],
                    "Land": row[5]
                }
                result = db.adressen.insert_one(adresse)
                id_mapping_adressen[current_adress_id] = result.inserted_id
                current_adress_id += 1

            elif row[0] == 'Nutzer':
                nutzer = {
                    "Info": row[1],
                    "Profilbild": row[2],
                    "Email": row[3],
                    "NutzerTyp": row[4],
                    "Bannerbild": row[5]
                }
                result = db.nutzer.insert_one(nutzer)
                id_mapping_nutzer[current_nutzer_id] = result.inserted_id
                current_nutzer_id += 1

            elif row[0] == 'Person':
                person = {
                    "Nutzer_ID": id_mapping_nutzer[int(row[1])],  # Verknüpfung mit Nutzer-ID
                    "Vorname": row[2],
                    "Nachname": row[3],
                    "Geburtstag": datetime.datetime.strptime(row[4], '%Y-%m-%d'),
                    "Beruf": row[5],
                    "Beschreibung": row[6],
                    "Adresse_ID": id_mapping_adressen[int(row[7])]  # Verknüpfung mit Adress-ID
                }
                db.personen.insert_one(person)

            elif row[0] == 'Kenntnisse':
                nutzer_id = int(row[1])  # Nutzer-ID aus CSV
                kenntnis = row[2]  # Die spezifische Kenntnis

                # Füge die Kenntnis dem zugehörigen Personendokument hinzu, indem die Nutzer-ID verwendet wird
                # Wir nehmen an, dass das Personendokument bereits eine Referenz auf die Nutzer-ID enthält
                person_document = db.personen.find_one({"Nutzer_ID": id_mapping_nutzer[nutzer_id]})
                if person_document:
                    db.personen.update_one(
                        {"_id": person_document['_id']},
                        {"$push": {"kenntnisse": kenntnis}}
                    )

            elif row[0] == 'Unternehmen':
                unternehmen = {
                    "NutzerID": id_mapping_nutzer[int(row[1])],
                    "Name": row[2],
                    "Branche": row[3],
                    "Groesse": row[4],
                    "Gruendungsjahr": row[5],
                    "Standorte": [],
                    "Stellenangebote": []
                }
                db.unternehmen.insert_one(unternehmen)

            elif row[0] == 'Standort':
                standort = {
                    "Standortname": row[1],
                    "AdresseID": id_mapping_adressen[int(row[2])]
                }
                standort_id = current_standort_id
                id_mapping_standort[standort_id] = standort
                current_standort_id += 1
                # Füge Standort zum entsprechenden Unternehmen hinzu
                db.unternehmen.update_one(
                    {"NutzerID": id_mapping_nutzer[int(row[3])]},
                    {"$push": {"Standorte": standort}}
                )
            elif row[0] == 'Stellenangebot':
                stellenangebot = {
                    "StandortID": id_mapping_standort[int(row[1])],  # Referenz zum Standort-Objekt
                    "Beschreibung": row[2],
                    "Titel": row[3]
                }
                # Füge Stellenangebot zum entsprechenden Unternehmen hinzu
                db.unternehmen.update_one(
                    {"NutzerID": id_mapping_nutzer[int(row[4])]},
                    {"$push": {"Stellenangebote": stellenangebot}}
                )


def clear_data():
    client.drop_database('meinedatenbank')
    print("Datenbank wurde gelöscht.")


def execute_query2(gesuchte_kenntnis):
    # Aggregationspipeline
    pipeline = [
        {
            "$match": {
                "kenntnisse": gesuchte_kenntnis  # Nutzt die Variable für den Filter
            }
        },
        {
            "$project": {
                "Nutzer_ID": 1,
                "Vorname": 1,
                "Nachname": 1,
                "Kenntnisse": {
                    "$filter": {
                        "input": "$kenntnisse",
                        "as": "kenntnis",
                        "cond": {"$eq": ["$$kenntnis", gesuchte_kenntnis]}  # Nutzt die Variable für den spezifischen Filter
                    }
                }
            }
        }
    ]

    # Ausführen der Pipeline
    results = list(db.personen.aggregate(pipeline))

    # Ergebnisse ausgeben
    for result in results:
        print(result)



def execute_query3(unternehmensname):
    # Aggregationspipeline
    pipeline = [
        {
            "$match": {
                "Name": unternehmensname  # Filtert die Dokumente nach dem Unternehmensnamen
            }
        },
        {
            "$unwind": {
                "path": "$Stellenangebote",
                "preserveNullAndEmptyArrays": True  # Stellen sicher, dass Unternehmen ohne Stellenangebote in der Zählung als 0 erscheinen
            }
        },
        {
            "$group": {
                "_id": "$Name",
                "Anzahl_der_Stellenangebote": {"$sum": 1}  # Summiert die Anzahl der Stellenangebote
            }
        }
    ]

    # Ausführen der Pipeline
    results = list(db.unternehmen.aggregate(pipeline))

    # Ergebnisse ausgeben
    if results:
        for result in results:
            print(f"Unternehmen: {result['_id']}, Anzahl der offenen Stellenangebote: {result['Anzahl_der_Stellenangebote']}")
    else:
        print("Keine Stellenangebote gefunden oder Unternehmen existiert nicht.")




def main():
    #load_data()
    #clear_data()




    start_time = time.time()
    execute_query2("word")
    end_time = time.time()
    print(f"Query Execution Time: {end_time - start_time:.4f} seconds")

    start_time = time.time()
    execute_query3("Solomon-Beck")
    end_time = time.time()
    print(f"Query Execution Time: {end_time - start_time:.4f} seconds")


if __name__ == '__main__':
    main()