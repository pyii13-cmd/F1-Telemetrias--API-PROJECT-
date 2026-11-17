# F1 · Degradació dels pneumàtics a Mònaco 2024

## Obrir el dashboard

1. A Windows, fes clic dret sobre el ZIP i tria **Extreu-ho tot**.
2. Entra a la carpeta F1 extreta i fes doble clic a **dashboard.html**. També pots obrir-lo des de PowerShell amb `Start-Process .\dashboard.html`. **run.bat** obre el mateix fitxer.
3. Prem **HARD**, **MEDIUM** o **SOFT**. El gràfic i la taula canvien junts. La capçalera resumeix tota la cursa. Pots obrir el fitxer amb Edge, Chrome o Firefox sense instal·lar paquets ni iniciar un servidor.

Per preparar la defensa, llegeix **GUIA_DEFENSA.md**. Els gràfics originals de detall són a **data/plots/**.

## Regenerar la vista a partir del CSV

Des de PowerShell, dins de la carpeta F1, executa `python src/web_exporter.py`. Només cal Python 3. S'actualitzen dashboard.html i data/dashboard_data.json. Torna a obrir el navegador o refresca la pàgina. Si el CSV correspon a una altra cursa, passa'n el nom amb `--race "2024 Bahrain Grand Prix"`. El CSV original no incorpora l'any ni el circuit.

## Tornar a calcular l'anàlisi amb FastF1

Pas opcional. Des de la carpeta F1, amb una versió de Python compatible amb les dependències:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Configura YEAR, GP i TEAMS dins de main.py abans del càlcul. Aquest procés escriu resultats a data i regenera el dashboard. Necessita accés a les dades de FastF1. El ZIP lleuger inclou el CSV i els 13 PNG. Per reutilitzar la memòria cau antiga, extreu només la carpeta data/cache del teu data.zip.zip dins de F1/data. Una versió diferent de FastF1 pot necessitar tornar a baixar dades.

## Aplicació anterior

El codi Streamlit original es conserva a app_streamlit_original.py per estudiar les cinc pestanyes. La comanda històrica adaptada al nou nom és `.\.venv\Scripts\python.exe -m streamlit run app_streamlit_original.py`. Aquesta via conserva les limitacions de l'original. El nou app.py és una drecera Python que obre el mateix HTML que run.bat.
