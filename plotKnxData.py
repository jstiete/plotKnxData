#!/usr/bin/env python3
# coding: utf-8

''' plotKnxData.py
    Getestet mit ETS 5.7.4
    Telegramme im Gruppenmonitor aufnehmen und als csv Datei speichern. 
    Vorheriges filtern ist nicht nötig, verringert aber ggf. die Rechen- und Speicherbedarfe.
    
    Export der Tabelle enthält folgende Spalten:
    #, Time, Service, Flags, Prio, Source Address, Source Name, Destination Address, Destination Name, Rout, Type, DPT, Info, Iack
    
    Anwendung: Eingabeaufforderung starten und im Ordner 'python plotKnxData.py --help' aufrufen.
'''

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import getopt
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.propagate = 0
# Logger für Konsole erstellen:
logFormatter = logging.Formatter('%(asctime)s\t- %(levelname)s\t- %(filename)s:(%(lineno)d) - %(message)s')
ch = logging.StreamHandler()
ch.setFormatter(logFormatter)
ch.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(ch)

##############################################################################
def printHelp():
    print("\nAufruf: plotKnxData.py -i [-o] [-t] [-n] Daten_Plot_1 [Daten_Plot_2..n]\n")
    print("-i [--ifile]\t Pfad zur csv-Datei.")
    print("-o [--ofile]\t Pfad für Ausgabe der erzeugten Figure. (Optional) PNG-Export siehe unten.")
    print("-t [--title]\t Titel des gesamten Diagramms. (Optional)")
    print("-n [--name]\t Titel der einzelnen Diagramme/Subplots. (Optional)")
    print("-h [--help]\t Zeigt diese Hilfe.\n")
    print("<Daten_Plot_n>\t Gruppenadressen zu einem Graphen zuordnen.\n\
      \t\t Bsp: 1/1/0 1/1/1 1/1/0,1/1/2 ordnet die Gruppenadresse 1/1/0 dem ersten Graphen zu, \n\
      \t\t 1/1/1 dem zweiten Graphen, der dritte Graph enthält die Gruppenadressen 1/1/1 und 1/1/2.\n")
    print("Ein Export als PNG-Datei kann in der angezeigten Figure erfolgen -> Button \'Save the figure\'.\n\n")
    print("Beispiele:\n\
           plotKnxData.py -i \"C:/My KNX Data.csv\" 1/1/0 oder plotKnxData.py --ifile \"My KNX Data.csv\" 1/1/0 \n\
             \tAngabe eines absoluten oder relativen Pfades. Verwendung von \"\", wenn der Parameter Leerzeichen enthält.\n\n\
           plotKnxData.py -i C:/My_KNX_Data.csv 4/1/255 1/1/2,1/5/2\n\
             \tAusgabe folgender Gruppenadressen Graph 1: 4/1/255,  Graph 2: 1/1/2, 1/5/2\n\n\
           plotKnxData.py -i C:/My_KNX_Data.csv -o myFigure.fig 1/1/2\n\
             \tAusgabe der Gruppenadresse 1/1/2 und speichern der Figure unter ./myFigure.fig \n\n\
           plotKnxData.py -i C:/My_KNX_Data.csv -t \"Temperaturen im Haus\" -n \"Dachgeschoss, Erdgeschoss\" 1/1/1 2/1/1,2/1/2\n\
             \tDiagramm mit Titel und Namen für die Diagramme. Ein Datensatz für Dachgeschoss, zwei Datensätze für Erdgeschoss.\n")
    return
##############################################################################

def decode_1xxx(input): #Schalten
    '''KNX DPT 1.xxx: 1-Bit Werte. Hexadezimal ausgegeben. Zwischen \$\ und \'|\''''
    try:
        #value = re.search(r'\$(([0-9A-Fa-f]{2}\s?)+)\s?\|',input).group(1) # suche alle Zweiergruppen(00-FF) mit optionalem Leerzeichen innerhalb '$ ... |'
        value = re.search(r'\$(.+?)\|',input).group(1) #substring zwischen '$' und ' |' suchen.
        value=int(value,16)
    except:
        logging.error("Konvertiere DPT=1.xxx Schalten: \"%s\" -> %s"%(input,str(value)),sys.exc_info()[0])
        value=0
    logging.debug("Konvertiere DPT=1.xxx Schalten: \"%s\" -> %d"%(input,value))
    return value

def decode_5xxx(input,max):
    '''KNX DPT 5.xxx 1-Byte unsigned int: Wertebereich 0...255
    Je nach DPT skaliert auf versch. Maximalwerte'''
    try:
        value = re.search(r'\$(.+?)\|',input).group(1) #suche substring zwischen '$' und ' |'
        value=int(value,16)
        value=int(round(value*max/255))
    except:
        logging.error("Konvertiere DPT=5.xxx 8-Bit unsigned (max=%d): \"%s\" -> %s"%(input,str(value)),sys.exc_info()[0])
        value=0
    logging.debug("Konvertiere DPT=5.xxx 8-Bit unsigned (max=%d): \"%s\" -> %.2f"%(max,input,value))
    return value

def decode_9001(input): #Temperatur
    '''KNX DPT 9.001: 2-Byte Floatingpoint 0bSEEEMMM 0bMMMMMMMM
    input: String mit Rohdaten und dekodierten Daten
       S: Vorzeichen (1 Bit)
       E: Exponent   (4 Bit)
       M: Mantisse  (12 Bit)'''
    byte1=int(input[0:2],16)            # SEEEMMM
    byte2=int(input[3:5],16)            # MMMMMMMM
    e=(byte1 & 0b01111000)>>3           # 0b00001111
    m=((byte1 & 0b00000111)<<8) | byte2 # 0b00000111 11111111
    s=((byte1 & 0b10000000))            # 0b10000000
    if s:
        m=m-2**11 # Mantisse sind 12Bit (inkl. Vorzeichen) max Wert = 2^11
    value=m*0.01*2**e
    logging.debug("Konvertiere DPT=9.001 Temperatur: \"%s\" -> %.2f°C"%(input,value))
    return value

def default_decoder(input):
    logging.warn("Ungültiger Datentyp! Decoder implementieren!")
    return 0
    
    #Funktionspointer fuer Konvertierung der Rohdaten
def convertDPT(dpt,returnUnit=False):
    '''Gibt je nach Aufruf einen Funktionspointer oder die verwendete Einheit zurück.'''
    from functools import partial
    switcher={
        #DPT   :  (Funktion,                      Einheit)
        '1.001':  (decode_1xxx,                   ''),
        '1.002':  (decode_1xxx,                   ''),
        '1.011':  (decode_1xxx,                   ''),
        '1.024':  (decode_1xxx,                   ''),
        '5.001':  (partial(decode_5xxx, max=100), '%'),
        '5.002':  (partial(decode_5xxx, max=360), '°'),
        '5.003':  (partial(decode_5xxx, max=255), '%'),
        '5.004':  (partial(decode_5xxx, max=255), ''),
        '9.001':  (decode_9001,                   '°C')}
    if(returnUnit):
        unit=switcher.get(dpt,(default_decoder, ''))[1] #->Index 1 des Tuples zurückgeben
        return unit
    func=switcher.get(dpt,(default_decoder, ''))[0]     #->Index 0 des Tuples zurückgeben
    return func

def dptTest():
    '''Testfunktion für die Decodierung der verwendeten Datentypen.
    Logging Level auf DEBUG stellen!'''
    myList=[]
    myList.append({'DPT':  '1.001 Schalten',          'Info': '$01 | Ein'})
    myList.append({'DPT':  '1.011 Status',            'Info': '$00 | Inaktiv'})
    myList.append({'DPT':  '5.001 Prozent (0..100%)', 'Info': '$30 | 19 %'})
    myList.append({'DPT':  '9.001 Temperatur (Â°C)',  'Info': '0C 47 | 21,9 Â°C'})
    myList.append({'DPT': '10.001 Tageszeit',         'Info': 'B0 26 27 | Freitag, 16:38:39'})
    myList.append({'DPT': '19.001 Datum/Zeit',        'Info': '79 01 08 B0 26 27 40 80 | Freitag, 08.01.2021, 16:38:39'})
    df=pd.DataFrame(myList)
    for i in range(len(df)) : 
        DPT =df.loc[i, 'DPT']
        INFO=df.loc[i, 'Info']
        dpt = re.search(r'[0-9]+\.[0-9]{3}',DPT).group(0)
        try:
            value=convertDPT(dpt)(INFO)
            logging.debug("Konvert DPT %s Value=\'%s\' zu %s"%(dpt,INFO,str(value)))
        except:
            logging.error('FEHLER! In DPT=',DPT," Info=%s"%INFO)
            logging.error(sys.exc_info()[0])
            pass


####################################################################################
###                           Main Schleife                                      ###
####################################################################################

if __name__ == '__main__':
    ######################################################################
    ## Übergabeparameter verarbeiten
    try:
        opts,args = getopt.getopt(sys.argv[1:],"hi:o:n:t:",["help","ifile=","ofile=","name=","title="])
    except getopts.GetoptError:
        printHelp()
        sys.exit(2)

    outputfile=None
    names=[]
    title=''
    for opt,arg in opts:
        if opt in ("-h","--help"):
            printHelp()
            sys.exit()
        try:
            if opt in ("-i", "--ifile"):
                inputfile=os.path.abspath(arg)
                logging.debug("Inputfile: %s"%inputfile)
            if opt in ("-o", "--ofile"):
                outputfile=os.path.abspath(arg)
                logging.debug("Outputfile: %s"%outputfile)
            if opt in ("-n", "--name"):
                names=re.split(r'\s*,\s*',arg)
                logging.info("Names: %s"%(','.join(names)))
            if opt in ("-t", "--title"):
                title=arg
                logging.info("Titel: %s"%title)
        except:
            print("Option: --help für Hilfe")
            print("FEHLER: ",sys.exc_info()[0])
            sys.exit(2)


    ######################################################################
    ## Datensatz einlesen und vorfiltern
    try:
        logging.info("Lese Datensatz von %s"%inputfile)
        with open(inputfile, "r") as fp:
            df=pd.read_csv(fp, sep=",", encoding = "utf-8")
    except:
        print("Fehler beim einlesen der Daten", sys.exc_info()[0])
        print("\n\n*******************************************************\n")
        printHelp()
        raise
    # Menge der Daten berechnen:
    columnNames = df.columns.values
    anzRow=len(df[['#']])
    logging.info("Datensatz eingelesen. %d Zeilen:\n%s"%(anzRow,df.head()))

    #Nur Zeilen mit Typ=GroupValueWrite verwenden.
    #ToDo: Ggf. erweitern oder anpassen.
    #HowTo: Filter in Pandas anwenden:
    #https://www.delftstack.com/de/howto/python-pandas/how-to-filter-dataframe-rows-based-on-column-values-in-pandas/
    #https://www.geeksforgeeks.org/python-pandas-dataframe-isin/
    filter=df['Type'].isin(['GroupValueWrite']) # Liste kann beliebig viele Werte enthalten (or condition)
    df = df[filter]                             # Verknüpfung von Filtern: df=df[filter1 & filter2]

    ######################################################################
    ## Liste mit alle Gruppenadressen und deren Häufigkeit erstellen.
    destAdr=df[['Destination Address']].copy()
    sDestAdr=destAdr['Destination Address'].value_counts()
    sDestAdr.sort_index(ascending=True, inplace=True)
    logging.debug("Gruppenadressen und Anzahl der Telegramme:",sDestAdr.head())


    ######################################################################
    ## Anordnung der Subplots parsen.

    # Werte anzeigen anhand von 'Destination Adress'
    # subplots enthält Liste der Subplots. Jeder Subplot ist ein dict mit den Daten.
    # Jeder Key im jeweiligen dict repräsentiert einen Datensatz, alle Keys zusammen bilden die Daten für einen Subplot.
    '''args=["9/0/4", "11/2/9,11/2/0", "0/7/0"]'''
    subplots=[]
    if args != []:          #args="1/1/2" "1/1/2,1/3/5"
        try:
            for arg in args: # testen, ob string eine gültige Adresse ist?
                    listOfAdresses=[]
                    listOfAdresses=arg.split(',')
                    dict={}
                    for adress in listOfAdresses:
                        if adress in sDestAdr.keys():
                            logging.info('Address %s: found %d entries.'%(adress,sDestAdr[adress]))
                            filter=df['Destination Address'].isin([adress])
                            dict[adress]=df[filter]
                        else:
                            raise InputError('Adresse %s wurde nicht gefunden!'%str(adress))
                    if bool(dict):
                        subplots.append(dict)
        except:
            logging.error("Fehler einlesen der Parameter: %s"%','.join(args), sys.exc_info()[0])
            printHelp()
    else:
        printHelp()
        sys.exit()
    # subplots=[dict_1, dict_2, ...]
    # dict_1={'Destination Address': pd.DataFrame} -> DataFrame enthält nur die Zeilen, die mit Destination Address übereinstimmen.

    # Länge von names auf Länge von subplots anpassen
    if len(subplots) != len(names):
        lN=len(names)
        lS=len(subplots)
        if lN>0:     #Parameter -n wurde verwendet aber in ungleicher Anzahl wie Menge der Diagramme
            msg='Anzahl der Elemente in -n / --name (%d) ist ungleich der Anzahl der Diagramme (Eingabeparameter) (%d)'%(lN,lS)
            logging.warn(msg)
        if lN<lS:    #Wenn weniger, dann auffüllen
            l=lS-lN
            tmpList=['']*l
            names.extend(tmpList)


    ######################################################################
    ## aufgenommene Signale plotten
    fig = plt.figure()
    if bool(title):
        fig.canvas.set_window_title(title)
        fig.suptitle(title)
    idx = len(subplots)*100+10+1
    for i in range(0,len(subplots)):
        axis=None
        if i==0:
            #Erster Subplot
            axis=fig.add_subplot(idx+i) #bsp. 211 = 2 Reihen, 1 Spalte, Index 1
        else:
            axis=fig.add_subplot(idx+i, sharex=fig.get_axes()[0])
        #Konvertiere Telegram-Daten zu plot-barem Format und füge Daten zu Diagramm hinzu:
        for addr,dfData in subplots[i].items():
            #'Destination Name' ermitteln
            destName=''
            if not (dfData['Destination Name'].empty):
                # '-' ausschließen. Keine Ahnung wo das herkommt.
                filter=dfData['Destination Name'].isin(['-'])
                destName=dfData[~filter]['Destination Name'].values[0]
            #Konvertiere 'Time' vom string zu datetime
            #dfData['Time']=pd.to_datetime(dfData['Time'],format="%d.%m.%YÂ %H:%M:%S,%f")
            dfData.loc[:,'Time']=pd.to_datetime(dfData['Time'],format="%d.%m.%YÂ %H:%M:%S,%f")
            #Daten entsprechend Datentyp konvertieren:
            dpt=dfData['DPT'].values[0]
            dpt = re.search(r'[0-9]+\.[0-9]{3}',dpt).group(0)
            dfData.loc[:,'Values'] = dfData['Info'].apply(convertDPT(dpt))
            #Label anpassen: 0/0/0 Adressenbezeichnung [Einheit]
            unit=convertDPT(dpt,returnUnit=True)
            label=str(addr)+' '+destName
            if bool(unit):
                label=label+' [%s]'%unit
            #Plot erstellen
            dfData.plot(x='Time', y='Values', ax=axis, label=label)
            dateFmt = mdates.DateFormatter('%Y-%m-%d %H:%M:%S')
            axis.xaxis.set_major_formatter(dateFmt)
        axis.set_title(names[i])
        axis.grid(True)
    #fig.tight_layout()
    fig.autofmt_xdate()

    #Export der Figure als binary (auch mit synchronisierten x-Achsen)
    #Der Export muss vor plt.show() erfolgen!
    if outputfile != None:
        try:
            import pickle
            pickle.dump(fig, open(outputfile, 'wb'))
        except:
            logging.error("Fehler Speichern der Ausgabedatei:", sys.exc_info()[0])

    #Diagrammfenster öffnen
    plt.show()
