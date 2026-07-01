#!/bin/bash
# Script de preparación e inicialización de Neo4j para Farmacia Americana

echo "=========================================================="
echo "Iniciando configuración de Neo4j (Grafos Médicos)..."
echo "=========================================================="

# 1. Crear la estructura de carpetas necesaria para los volúmenes
echo "1. Creando directorios de volúmenes locales (neo4j_data)..."
mkdir -p neo4j_data/data
mkdir -p neo4j_data/logs
mkdir -p neo4j_data/import
mkdir -p neo4j_data/plugins

# Dar permisos abiertos temporales a las carpetas para que el usuario 'neo4j' de Docker pueda escribir
chmod -R 777 neo4j_data

# 2. Descargar el Plugin Neosemantics (n10s)
# Este plugin no se auto-descarga por Docker, hay que inyectarlo manualmente
N10S_VERSION="5.23.0"
PLUGIN_URL="https://github.com/neo4j-labs/neosemantics/releases/download/${N10S_VERSION}/neosemantics-${N10S_VERSION}.jar"
PLUGIN_DEST="neo4j_data/plugins/neosemantics-${N10S_VERSION}.jar"

if [ -f "$PLUGIN_DEST" ]; then
    echo "2. El plugin Neosemantics ya existe. Omitiendo descarga."
else
    echo "2. Descargando plugin Neosemantics (n10s) v${N10S_VERSION}..."
    wget -q --show-progress -O "$PLUGIN_DEST" "$PLUGIN_URL"
    if [ $? -eq 0 ]; then
        echo "   -> Plugin descargado exitosamente."
    else
        echo "   -> Error descargando el plugin. Por favor revisa la conexión."
    fi
fi

# 3. Levantar el contenedor
echo "3. Levantando contenedor de Neo4j en background..."
docker compose -f docker-neo4j-compose.yml up -d

echo "=========================================================="
echo "✅ Despliegue completado."
echo "La consola visual de Neo4j estará disponible en unos segundos en:"
echo "http://localhost:7474  (Usuario: neo4j / Password: Twinc3pt.2)"
echo "Las ontologías (Archivos OWL/RDF) deben copiarse dentro de la carpeta: ./neo4j_data/import/"
echo "=========================================================="
