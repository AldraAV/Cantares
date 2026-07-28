# -*- coding: utf-8 -*-
"""
Script de automatizacion de Cantares para descargar la Biblioteca de Estudio y Roadmap Universitario.
Utiliza la conexion programatica de AnnasArchiveSearcher y BookDownloader de Cantares.
"""

import os
import sys
import time
import json
import re

# Forzar codificacion utf-8 o reemplazo en stdout de Windows para evitar errores cp1252
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from cantares.books.annas_archive import AnnasArchiveSearcher
    from cantares.books.downloader import BookDownloader
except ImportError as e:
    print(f"[ERROR] No se pudo importar cantares.books: {e}")
    sys.exit(1)

# Lista oficial de libros solicitados en el Roadmap
LIBROS_ROADMAP = [
    {
        "titulo_completo": "Fundamentos de Programacion - Luis Joyanes Aguilar",
        "busquedas": [
            "Luis Joyanes Aguilar Fundamentos de programacion",
            "Joyanes Aguilar Fundamentos programacion"
        ],
        "archivo_esperado": "Fundamentos_de_Programacion_Luis_Joyanes_Aguilar"
    },
    {
        "titulo_completo": "Matematicas Discretas y sus Aplicaciones - Kenneth H. Rosen",
        "busquedas": [
            "Kenneth Rosen Matematicas discretas y sus aplicaciones",
            "Kenneth H Rosen Discrete Mathematics"
        ],
        "archivo_esperado": "Matematicas_Discretas_Kenneth_Rosen"
    },
    {
        "titulo_completo": "Fundamentos de Bases de Datos - Abraham Silberschatz",
        "busquedas": [
            "Abraham Silberschatz Fundamentos de bases de datos",
            "Silberschatz Database System Concepts"
        ],
        "archivo_esperado": "Fundamentos_Bases_Datos_Abraham_Silberschatz"
    },
    {
        "titulo_completo": "Primeros pasos con FastAPI - Andres Cruz Yoris",
        "busquedas": [
            "Andres Cruz Yoris Primeros pasos con FastAPI",
            "Primeros pasos con FastAPI"
        ],
        "archivo_esperado": "Primeros_pasos_con_FastAPI_Andres_Cruz_Yoris"
    },
    {
        "titulo_completo": "FastAPI - Bill Lubanovic / O'Reilly",
        "busquedas": [
            "Bill Lubanovic FastAPI",
            "FastAPI Modern Python Web Development Lubanovic"
        ],
        "archivo_esperado": "FastAPI_Bill_Lubanovic_OReilly"
    },
    {
        "titulo_completo": "Python para Analisis de Datos - Wes McKinney",
        "busquedas": [
            "Wes McKinney Python para analisis de datos",
            "Wes McKinney Python for Data Analysis"
        ],
        "archivo_esperado": "Python_para_Analisis_de_Datos_Wes_McKinney"
    },
    {
        "titulo_completo": "R para Ciencia de Datos - Hadley Wickham",
        "busquedas": [
            "Hadley Wickham R para ciencia de datos",
            "Hadley Wickham R for Data Science"
        ],
        "archivo_esperado": "R_para_Ciencia_de_Datos_Hadley_Wickham"
    },
    {
        "titulo_completo": "Estructuras de Datos y Algoritmos en C++ - Adam Drozdek",
        "busquedas": [
            "Adam Drozdek Estructuras de datos y algoritmos en C++",
            "Adam Drozdek Data Structures and Algorithms in C++"
        ],
        "archivo_esperado": "Estructuras_de_Datos_y_Algoritmos_C++_Adam_Drozdek"
    },
    {
        "titulo_completo": "Desarrollo de videojuegos con C++ Vol 1 - Elisa Belmar",
        "busquedas": [
            "Elisa Belmar Desarrollo de videojuegos con C++",
            "Desarrollo de videojuegos con C++ Elisa Belmar"
        ],
        "archivo_esperado": "Desarrollo_Videojuegos_C++_Vol1_Elisa_Belmar"
    },
    {
        "titulo_completo": "Aprende programacion con C++ - Jose Vicente Carratala",
        "busquedas": [
            "Jose Vicente Carratala Aprende programacion con C++",
            "Jose Vicente Carratala C++"
        ],
        "archivo_esperado": "Aprende_Programacion_C++_Jose_Vicente_Carratala"
    },
    {
        "titulo_completo": "Programacion en Go - Mario Macias Lloret",
        "busquedas": [
            "Mario Macias Lloret Programacion en Go",
            "Programacion en Go Mario Macias"
        ],
        "archivo_esperado": "Programacion_en_Go_Mario_Macias_Lloret"
    },
    {
        "titulo_completo": "Programacion C# Edicion 2023 Para Principiantes - Antonio Vargas Banuelos",
        "busquedas": [
            "Antonio Vargas Banuelos Programacion C#",
            "Programacion C# Para Principiantes Antonio Vargas"
        ],
        "archivo_esperado": "Programacion_CSharp_2023_Antonio_Vargas_Banuelos"
    },
    {
        "titulo_completo": "React Native: Aprende a crear aplicaciones moviles en un fin de semana - Joan Cruz Navas",
        "busquedas": [
            "Joan Cruz Navas React Native",
            "React Native Aprende a crear aplicaciones moviles en un fin de semana"
        ],
        "archivo_esperado": "React_Native_Fin_de_Semana_Joan_Cruz_Navas"
    },
    {
        "titulo_completo": "Codigo Limpio (Clean Code) - Robert C. Martin",
        "busquedas": [
            "Robert C Martin Codigo Limpio",
            "Robert C Martin Clean Code"
        ],
        "archivo_esperado": "Codigo_Limpio_Clean_Code_Robert_C_Martin"
    },
    {
        "titulo_completo": "Arquitectura Limpia - Robert C. Martin",
        "busquedas": [
            "Robert C Martin Arquitectura Limpia",
            "Robert C Martin Clean Architecture"
        ],
        "archivo_esperado": "Arquitectura_Limpia_Robert_C_Martin"
    },
    {
        "titulo_completo": "Teoria de la Musica - Francisco Moncada Garcia",
        "busquedas": [
            "Francisco Moncada Garcia Teoria de la musica",
            "Moncada Garcia Teoria de la musica"
        ],
        "archivo_esperado": "Teoria_de_la_Musica_Francisco_Moncada_Garcia"
    },
    {
        "titulo_completo": "Armonia - Walter Piston",
        "busquedas": [
            "Walter Piston Armonia",
            "Walter Piston Harmony"
        ],
        "archivo_esperado": "Armonia_Walter_Piston"
    },
    {
        "titulo_completo": "Guitarra para Dummies - Mark Phillips",
        "busquedas": [
            "Mark Phillips Guitarra para Dummies",
            "Mark Phillips Guitar for Dummies"
        ],
        "archivo_esperado": "Guitarra_para_Dummies_Mark_Phillips"
    },
    {
        "titulo_completo": "Practical C++ Programming - Steve Oualline / O'Reilly - Ardilla",
        "busquedas": [
            "Steve Oualline Practical C++ Programming",
            "Practical C++ Programming Oualline"
        ],
        "archivo_esperado": "Practical_C++_Programming_Steve_Oualline_OReilly"
    },
    {
        "titulo_completo": "Learning Go - Jon Bodner / O'Reilly - Ganso",
        "busquedas": [
            "Jon Bodner Learning Go",
            "Learning Go Bodner OReilly"
        ],
        "archivo_esperado": "Learning_Go_Jon_Bodner_OReilly"
    },
    {
        "titulo_completo": "Programming Rust - Jim Blandy / O'Reilly - Cangrejo",
        "busquedas": [
            "Jim Blandy Programming Rust",
            "Programming Rust Blandy OReilly"
        ],
        "archivo_esperado": "Programming_Rust_Jim_Blandy_OReilly"
    },
    {
        "titulo_completo": "Learning the vi and Vim Editors - Arnold Robbins / O'Reilly - Tarsero",
        "busquedas": [
            "Arnold Robbins Learning the vi and Vim Editors",
            "Learning the vi and Vim Editors OReilly"
        ],
        "archivo_esperado": "Learning_vi_Vim_Editors_Arnold_Robbins_OReilly"
    }
]

def limpiar_nombre_archivo(nombre: str) -> str:
    nombre_limpio = re.sub(r'[\\/*?:"<>|]', "", nombre)
    nombre_limpio = nombre_limpio.replace(" ", "_")
    return re.sub(r'_+', "_", nombre_limpio).strip("_")

def procesar_descargas():
    print("==========================================================================")
    print("[INFO] CANTARES - DESCARGADOR DE BIBLIOTECA UNIVERSITARIA Y ROADMAP")
    print("[INFO] Motor: Anna's Archive / LibGen Mirror Rotational Engine")
    print("==========================================================================")

    directorio_destino = os.path.join(os.path.abspath(os.path.dirname(__file__)), "Books")
    os.makedirs(directorio_destino, exist_ok=True)

    buscador = AnnasArchiveSearcher()
    descargador = BookDownloader()

    resumen_resultados = []

    for indice, libro in enumerate(LIBROS_ROADMAP, 1):
        titulo_display = libro["titulo_completo"]
        nombre_base = libro["archivo_esperado"]

        print(f"\n--------------------------------------------------------------------------")
        print(f"[{indice}/{len(LIBROS_ROADMAP)}] Procesando: {titulo_display}")
        print(f"--------------------------------------------------------------------------")

        archivos_existentes = [f for f in os.listdir(directorio_destino) if f.startswith(nombre_base)]
        if archivos_existentes:
            print(f"[EXISTENTE] El libro ya fue descargado previamente: {archivos_existentes[0]}")
            resumen_resultados.append({
                "libro": titulo_display,
                "estado": "YA_EXISTENTE",
                "archivo": os.path.join(directorio_destino, archivos_existentes[0])
            })
            continue

        exito = False
        for intento_busqueda in libro["busquedas"]:
            print(f"[BUSCANDO] Consultando espejos con consulta: '{intento_busqueda}'...")
            try:
                resultados = buscador.search(intento_busqueda)
                if not resultados:
                    print(f"[ADVERTENCIA] Sin coincidencias para esta consulta, probando siguiente...")
                    continue

                candidatos_ordenados = sorted(
                    resultados,
                    key=lambda r: 0 if r["extension"].lower() in ["pdf", "epub"] else 1
                )
                seleccion = candidatos_ordenados[0]
                print(f"[ENCONTRADO] Candidato: {seleccion['title']} | Autor: {seleccion['author']} ({seleccion['extension']})")

                print(f"[ENLACE] Resolviendo enlace de descarga directo...")
                enlace_directo = buscador.get_download_link(seleccion["link"])

                if not enlace_directo:
                    print(f"[ERROR] No se pudo resolver un enlace de descarga directo desde {seleccion['link']}.")
                    continue

                extension_limpia = seleccion["extension"].lower().replace(".", "")
                if not extension_limpia:
                    extension_limpia = "pdf"

                nombre_final = f"{nombre_base}.{extension_limpia}"
                ruta_final = os.path.join(directorio_destino, nombre_final)

                print(f"[DESCARGANDO] Descargando archivo hacia: {nombre_final} ...")
                def reporte_progreso(actual, total):
                    if total > 0:
                        porcentaje = (actual / total) * 100
                        mb_actual = actual / (1024 * 1024)
                        mb_total = total / (1024 * 1024)
                        sys.stdout.write(f"\r    --> Progreso: {mb_actual:.2f} MB / {mb_total:.2f} MB ({porcentaje:.1f}%)")
                        sys.stdout.flush()

                descargador.download(enlace_directo, nombre_final, progress_callback=reporte_progreso)
                print("\n[EXITO] Descarga finalizada exitosamente.")

                resumen_resultados.append({
                    "libro": titulo_display,
                    "estado": "DESCARGADO",
                    "archivo": ruta_final
                })
                exito = True
                time.sleep(2)
                break

            except Exception as error_descarga:
                print(f"\n[ERROR] Error durante el intento '{intento_busqueda}': {error_descarga}")
                time.sleep(1)

        if not exito:
            print(f"[ADVERTENCIA] No fue posible descargar '{titulo_display}' en esta iteracion (espejos saturados o sin enlace libre).")
            resumen_resultados.append({
                "libro": titulo_display,
                "estado": "FALLIDO_O_SATURADO",
                "archivo": None
            })

    ruta_reporte = os.path.join(directorio_destino, "reporte_roadmap_descargas.json")
    with open(ruta_reporte, "w", encoding="utf-8") as archivo_reporte:
        json.dump(resumen_resultados, archivo_reporte, indent=4, ensure_ascii=False)

    print("\n==========================================================================")
    print(f"[FINALIZADO] Proceso completado. Reporte generado en: {ruta_reporte}")
    print("==========================================================================")

if __name__ == "__main__":
    procesar_descargas()
