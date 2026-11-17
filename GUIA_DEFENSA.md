# Com defensar l’anàlisi de pneumàtics de Mònaco 2024

## 1. Quina pregunta respon el projecte?

«Dins d’un mateix stint, com varia el temps per volta quan el pneumàtic acumula voltes?» Un **stint** és el tram que un pilot fa amb un joc de pneumàtics. Cada observació del model és una volta d’un pilot. El dashboard presenta un nivell més agregat: una fila per equip i compost. El CSV conté 14 combinacions, 9 equips, 3 compostos, 21 stints admesos i 1.130 voltes sumades entre pilots. Per això pots veure 146 voltes per Ferrari encara que una cursa individual tingui moltes menys voltes.

Distingeix tres variables. **LapNumber** situa el cotxe dins de la cursa. **TyreLife** indica l’edat del joc, que pot portar ús previ. **Stint** identifica el tram dins de la cursa del pilot. Per exemple, a la volta 40, un joc muntat fa poques voltes pot tenir una edat de 5. La correcció de combustible fa servir 40 i la regressió fa servir 5.

## 2. Recorregut d’una volta pels fitxers de src

### data_loader.py · De la sessió a una taula

F1DataLoader crea la carpeta de memòria cau i l’activa a FastF1. load_session demana any, Gran Premi i tipus de sessió, i carrega la sessió. get_race_data força el tipus R (cursa) i permet filtrar per equip. extract_laps_dataframe parteix de session.laps, permet filtrar per pilot, conserva les columnes d’interès i transforma LapTime a LapTimeSeconds. Un temps de 1:20.500 passa a 80,500 segons, més fàcil d’utilitzar en una regressió. Afegeix esdeveniment, any i tipus de sessió. També extreu FreshTyre i IsPersonalBest, encara que el model no els utilitza com a predictors. L’entrada de la regressió prové del cronometratge per volta. La velocitat instantània, el gas o el fre poden existir a la memòria cau però no entren en aquesta anàlisi.

### preprocessor.py · Quines voltes són comparables?

1. filter_valid_laps elimina temps absents i qualsevol volta amb PitInTime o PitOutTime informat. Entrar o sortir de boxes altera el temps per motius aliens al ritme del stint.
2. Exigeix TrackStatus exactament igual a la cadena '1'. Una volta amb una combinació d’estats també queda fora. En les voltes restants, calcula la mediana global i la desviació estàndard i conserva els temps estrictament dins de mediana ± 2 desviacions. El llindar global pot descartar voltes legítimes dels grups més extrems.
3. apply_fuel_correction calcula **temps corregit = temps mesurat + 0,040 × LapNumber**, amb el valor de main.py. A la volta 40, 80,500 s passen a 82,100 s. El signe és positiu perquè el model intenta compensar l’avantatge de portar menys combustible a mesura que avança la cursa. És una hipòtesi constant i el codi aplica una correcció més gran a les voltes tardanes.
4. prepare_stint_data exigeix TyreLife vàlida i positiva, ordena per pilot i volta i calcula estadístics auxiliars per stint. Retorna les voltes individuals. process coordina els passos i retorna també els recomptes, els equips, els pilots i els compostos. El nombre de voltes després de netejar pot superar el nombre final modelitzat pels llindars del pas següent.

### degradation_model.py · D’un núvol de punts a una fila del CSV

Per a cada equip i compost, analyze_by_compound exigeix almenys 10 voltes netes en total. Separa les files per **Driver + Stint**. Un “stint 2” de Leclerc i un “stint 2” d’un altre pilot són dues mostres diferents. analyze_stint exigeix 5 voltes per ajustar una recta. Per exemple, un grup de 12 voltes dividides en tres stints de quatre supera el primer llindar i acaba sense resultat.

fit_linear_model ajusta per mínims quadrats **temps corregit = β₀ + β₁ × TyreLife**. β₀ és el temps estimat a edat zero, una extrapolació perquè s’han exclòs les edats zero. β₁ mesura el canvi estimat en segons per cada volta addicional d’edat. Calcula també prediccions, residus (observat menys predit) i R². Un residu positiu indica una volta més lenta que la predicció. R² descriu com s’ajusta el model a les mateixes dades amb què s’ha entrenat.

Amb almenys 8 voltes prova també una quadràtica. La marca com a preferida si millora R² en més de 0,05. Aquesta decisió afecta la corba que es pot dibuixar per al stint. **El rànquing sempre agrega pendents lineals**, fins i tot quan la quadràtica ajusta millor. El camp del codi anomenat inflection_point calcula −b/(2a): és el vèrtex de la paràbola. Que aparegui un vèrtex no demostra un col·lapse físic del pneumàtic.

analyze_all_teams repeteix el càlcul per cada combinació i crea el CSV resum. Cada stint vàlid té el mateix pes en la mitjana dels pendents i dels interceptes. Per exemple, amb dos pendents +0,02 i +0,08, la mitjana és +0,05 encara que un stint sigui molt més llarg. Degradation_std és la desviació poblacional dels pendents dels stints amb numpy.std. Amb un sol stint, val zero per construcció. get_efficiency_ranking ordena per pendent ascendent dins del compost.

### visualizer.py · Què aporta cada família de gràfics?

DegradationVisualizer escriu PNG a data/plots amb Matplotlib. plot_degradation_by_team compara pendents i fa servir Degradation_std com a barres d’error. plot_compound_comparison posa els compostos disponibles en un mateix gràfic. plot_base_pace_vs_degradation presenta dues magnituds diferents: un cotxe pot tenir un ritme base ràpid i perdre més temps per volta. plot_stint_evolution dibuixa una observació per volta i superposa la recta o quadràtica seleccionada. La x és TyreLife i la y és el temps corregit. generate_all_plots tria el primer stint dels primers sis resultats per als exemples de detall. Aquesta selecció depèn de l’ordre dels resultats.

### web_exporter.py, dashboard_template.html i __init__.py

L’exportador original transformava el CSV en equips amb una llista de compostos, afegia colors i fixava el total de voltes a 1.138. L’HTML original tenia una còpia manual de les dades. A la versió reparada, l’exportador llegeix el CSV amb la biblioteca estàndard, calcula recomptes, escriu el JSON i insereix les mateixes dades dins de la plantilla per produir l’HTML autònom. La plantilla defineix el selector, la taula i les barres centrades a zero, amb una escala comuna als tres compostos. Edita la plantilla per canviar una vista que vulguis conservar després de regenerar-la. __init__.py identifica el paquet src i declara la versió 1.0.0. Els .pyc de __pycache__ a l’arxiu original són còpies compilades automàtiques per a Python 3.13.

## 3. Què fa cada fitxer de l’arrel?

| Fitxer | Paper dins del projecte |
|---|---|
| main.py | Coordina càrrega, neteja, modelització, exportació i gràfics. Per defecte selecciona Mònaco 2024 i tots els equips. Escriu el CSV i imprimeix al terminal equips, stints i rangs de pendents. En aquesta versió també actualitza el JSON i l’HTML. |
| app.py original, ara app_streamlit_original.py | Interfície Streamlit amb cinc pestanyes. Explora voltes per equip, pilot i stint, ordena mitjanes de temps corregit per compost i calcula el delta respecte al primer. També mostra degradació, sensibilitat al combustible i metodologia. La sensibilitat resta els pendents del primer i l’últim 30% de les files de l’equip ordenades per volta. Pot barrejar pilots i compostos: és una aproximació indirecta. |
| app.py actual | Obre dashboard.html al navegador des de Python, resolent la ruta respecte al mateix script. |
| dashboard.html | Fitxer que has d’obrir per ensenyar el treball. Conté estil, dades i interacció. Canviar el compost filtra les files de la cursa precalculada. |
| run.bat | Llançador de Windows. L’original apuntava a una ruta personal i al Python d’un entorn virtual concret. L’actual obre l’HTML situat al costat del BAT. |
| requirements.txt | Dependències de la via de recàlcul i de l’aplicació antiga: FastF1 obté la sessió, pandas manipula taules, NumPy calcula estadístics, scikit-learn ajusta models, SciPy s’utilitza a la sensibilitat, Matplotlib/Seaborn serveixen els gràfics estàtics i Streamlit/Plotly la interfície antiga. |
| server_8505.log | Registre històric. L’única línia indica que el port 8505 no estava disponible en aquell intent. No identifica quin procés l’ocupava ni explica totes les possibles fallades del programa. |
| README.md i GUIA_DEFENSA.md | El primer conté els passos d’execució. Aquesta guia explica les decisions i com interpretar-ne els resultats. |

L’original tenia tres vies diferents: main.py feia el càlcul per lots, Streamlit carregava una sessió en obrir l’app, i l’HTML mostrava resultats incrustats amb Chart.js descarregat d’Internet. A Streamlit, les funcions de memòria cau ignoraven els arguments de dades prefixats amb guió baix. Això podia reutilitzar un resultat anterior en canviar de cursa. A l’HTML, si Chart.js no carregava, la creació del gràfic podia interrompre la inicialització abans del rànquing. La demo reparada llegeix les dades incorporades i dibuixa les barres al mateix navegador.

## 4. Què hi ha exactament a data?

**degradation_summary.csv** és la font del dashboard reparat. Team i Compound identifiquen la fila. BasePace_s és l’intercepte mitjà, Degradation_s_per_lap el pendent mitjà, Degradation_std la dispersió entre stints, Stints el nombre d’ajustos vàlids i TotalLaps la suma de voltes dels stints vàlids. **dashboard_data.json** presenta els mateixos resultats agrupats per equip, juntament amb metadades. Si canvies una cel·la del CSV, executa l’exportador per actualitzar JSON i HTML.

**plots/** conserva els 13 PNG. compound_comparison_all_teams.png és la comparació global. degradation_by_team_hard/medium/soft.png són tres fitxers de pendents, i pace_vs_degradation_hard/medium/soft.png són tres fitxers de ritme contra pendent. Els sis noms que comencen per stint identifiquen equip, pilot, compost i número de stint: Alpine/GAS/MEDIUM/2, Aston Martin/ALO/MEDIUM/2, Aston Martin/STR/SOFT/4, Ferrari/LEC/HARD/2, Kick Sauber/BOT/HARD/3 i Kick Sauber/BOT/MEDIUM/2. El sufix s2.0 prové de com es va representar numèricament el número del stint.

**cache/**, dins del data.zip.zip original, té una base fastf1_http_cache.sqlite per reutilitzar respostes HTTP i tres carpetes de cursa: Mònaco 2023, Bahrain 2024 i Mònaco 2024. Tenir tres curses a la memòria cau no implica que el CSV les combini. A cadascuna es repeteixen aquests fitxers interns de FastF1:

| Fitxer .ff1pkl | Informació que identifica |
|---|---|
| car_data | Canals del cotxe al llarg del temps, com velocitat o accelerador. |
| position_data | Posició dels cotxes al llarg de la sessió. |
| driver_info | Identificació dels pilots. |
| lap_count | Evolució del comptador de voltes. |
| race_control_messages | Missatges de direcció de cursa. |
| session_info | Metadades identificatives de la sessió. |
| session_status_data | Canvis d’estat de la sessió. |
| timing_app_data | Informació de cronometratge complementària, incloses dades de stints i pneumàtics. |
| track_status_data | Canvis en l’estat de la pista; aquesta informació intervé en el filtre de pista verda. |
| weather_data | Observacions meteorològiques. El model presentat no té cap variable meteorològica. |
| _extended_timing_data | Dades de cronometratge processades a partir de les quals FastF1 pot reconstruir informació de les voltes. |

FastF1 gestiona aquests fitxers. El teu codi treballa amb session.laps. El ZIP de la demo conserva les sortides petites i prescindeix de la memòria cau, que ja tens al ZIP original.

## 5. Demostració oral amb xifres del teu CSV

**Primer, obre HARD.** Ferrari presenta −0,02151 s/volta i McLaren −0,02121, amb dos stints cadascun i 146 i 148 voltes respectivament. El rànquing posa Ferrari primer per una diferència aproximada de 0,00031 s/volta. Amb aquest resum no pots concloure que la diferència sigui estadísticament significativa.

**Canvia a SOFT.** Només apareix Aston Martin, amb un stint de 26 voltes i +0,04926 s/volta. Si compares les edats 5 i 15 dins de la recta ajustada, la diferència prevista és 10 × 0,04926 ≈ **0,493 segons en el temps d’una volta**. És una diferència entre dos temps previstos. La pèrdua acumulada al llarg de diverses voltes seria un càlcul diferent. Obre el PNG de STR amb SOFT per veure els punts que hi ha darrere d’aquesta fila.

**Acaba amb MEDIUM.** Kick Sauber té −0,20274 s/volta en només 11 voltes d’un stint. Un pendent negatiu significa que el ritme corregit va millorar durant aquell tram. Poden influir-hi el trànsit, la gestió del ritme, la pista o la hipòtesi de combustible. No s’ha mesurat el desgast físic de la goma. Tampoc pots extrapolar el pendent fins a qualsevol edat.

## 6. Preguntes que et poden fer

**Per què ajustes cada stint abans d’agrupar?** Barrejar directament dos pilots que roden a ritmes diferents podria crear un pendent fictici. Si el pilot més ràpid aporta sobretot voltes amb goma nova, part de la diferència entre pilots semblaria degradació. Ajustar cada tram conserva la comparació dins del mateix pilot i joc.

**Què canviaria si pugessis el factor de combustible de 0,040 a 0,050?** En un stint on LapNumber i TyreLife avancen junts, cada volta successiva rebria 0,010 s més de correcció que abans respecte a la precedent. El pendent ajustat pujaria aproximadament 0,010 s/volta. Això explica per què cal declarar el factor emprat.

**Per què SOFT té només un equip?** El CSV conté un únic grup que arriba al resum. Amb el resum sol no podem distingir els equips que no van utilitzar el compost dels que van perdre massa voltes en els filtres.

**Com milloraries la confiança en el resultat?** Compararia més stints en condicions semblants, provaria la sensibilitat al factor de combustible i separaria entrenament i validació per stint o per cursa. Això permetria comprovar si una quadràtica que millora R² en les voltes observades també prediu millor altres dades.

**Què calcules quan prems un botó del dashboard?** El navegador selecciona les files del compost, les ordena pel pendent i redibuixa les barres i la taula. Les regressions ja s’han fet. Aquesta separació permet repetir la demostració sense connexió.
