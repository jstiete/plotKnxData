# plotKnxData
plot knx telegrams from ets in pythons matplotlib

    Aufruf: plotKnxData.py -i [-o] [-t] [-n] Daten_Plot_1 [Daten_Plot_2..n]

    -i [--ifile]     Pfad zur csv-Datei.
    -o [--ofile]     Pfad für Ausgabe der erzeugten Figure. (Optional) PNG-Export siehe unten.
    -t [--title]     Titel des gesamten Diagramms. (Optional)
    -n [--name]      Titel der einzelnen Diagramme/Subplots. (Optional)
    -h [--help]      Zeigt diese Hilfe.

    Gruppenadressen zu einem Graphen zuordnen:
    <Daten_Plot_n>   Diagramme mit gemeinsamen Y-Achsen:
                     Bsp: 1/1/0 1/1/1 1/1/0,1/1/2 ordnet die Gruppenadresse 1/1/0 dem ersten Graphen zu,
                     1/1/1 dem zweiten Graphen, der dritte Graph enthält die Gruppenadressen 1/1/1 und 1/1/2.
    <Daten_Plot_n>   Getrennte Y-Achsen:
                     Bsp: 1/1/0:1/1/1 1/1/0,1/1/2:1/1/1 erstellt zwei Diagramme mit getrennen Y-Achsen.
                     Der erste Graph enthält auf der linken Y-Achse die Daten von 1/1/0, auf der rechten Y-Achse die Daten von 1/1/1.
                     Der zweite Graph enthält auf der linken Y-Achse die Daten von 1/1/0 und 1/1/2, auf der rechten Y-Achse die Daten von 1/1/1
    Ein Export als PNG-Datei kann in der angezeigten Figure erfolgen -> Button 'Save the figure'.


    Beispiele:
               plotKnxData.py -i "C:/My KNX Data.csv" 1/1/0 oder plotKnxData.py --ifile "My KNX Data.csv" 1/1/0
                    Angabe eines absoluten oder relativen Pfades. Verwendung von "", wenn der Parameter Leerzeichen enthält.

               plotKnxData.py -i C:/My_KNX_Data.csv 4/1/255 1/1/2,1/5/2
                    Ausgabe folgender Gruppenadressen Graph 1: 4/1/255,  Graph 2: 1/1/2, 1/5/2

               plotKnxData.py -i C:/My_KNX_Data.csv -o myFigure.fig 1/1/2
                    Ausgabe der Gruppenadresse 1/1/2 und speichern der Figure unter ./myFigure.fig

               plotKnxData.py -i C:/My_KNX_Data.csv -t "Temperaturen im Haus" -n "Dachgeschoss, Erdgeschoss" 1/1/1 2/1/1,2/1/2
                    Diagramm mit Titel und Namen für die Diagramme. Ein Datensatz für Dachgeschoss, zwei Datensätze für Erdgeschoss.
