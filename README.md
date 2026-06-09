# 🚀 IoT Data Ingestion Pipeline — Projet AWS

**Cours :** Ingénierie Big Data & IA  
**Date :** Juin 2026  
**Stack :** `devoir-iot-ksenou`  
**Région :** `eu-west-3` (Paris)

---

## Sommaire

1. [Contexte et Objectifs](#1-contexte-et-objectifs)
2. [Architecture Générale](#2-architecture-générale)
3. [Infrastructure as Code (CloudFormation)](#3-infrastructure-as-code-cloudformation)
4. [Déploiement de l'Infrastructure](#4-déploiement-de-linfrastructure)
5. [Code Lambda (Traitement à la volée)](#5-code-lambda-traitement-à-la-volée)
6. [Script Client de Test](#6-script-client-de-test)
7. [Site de Documentation Technique](#7-site-de-documentation-technique)
8. [Validation et Tests](#8-validation-et-tests)
9. [Monitoring et Gestion des Échecs](#9-monitoring-et-gestion-des-échecs)
10. [Réponses aux Questions Théoriques](#10-réponses-aux-questions-théoriques)
11. [Captures d'Écran](#11-captures-décran)
12. [Livrables](#12-livrables)

---

## 1. Contexte et Objectifs

### Contexte
Entreprise industrielle déployant des milliers de capteurs IoT. Besoin d'une architecture **hautement disponible** capable de capter les flux de données envoyés par requêtes HTTP POST en temps réel.

### Objectifs
- Pipeline d'ingestion temps réel via AWS Lambda
- Data Lake brut sur Amazon S3 avec partitionnement temporel
- Feature Store analytique sur Amazon DynamoDB
- CDN CloudFront devant l'API Gateway pour l'ingestion globale
- Site de documentation technique hébergé sur S3, accessible via CloudFront avec OAC
- Infrastructure entièrement automatisée avec CloudFormation (SAM)

---

## 2. Architecture Générale

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Capteurs    │────▶│  CloudFront  │────▶│  API Gateway │
│  IoT (POST)  │     │  (CDN)       │     │  /ingest     │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │   AWS Lambda  │
                                          │  (Python 3.11)│
                                          └──────┬───────┘
                                                 │
                              ┌──────────────────┼──────────────────┐
                              ▼                  ▼                  │
                     ┌──────────────┐   ┌──────────────┐            │
                     │  Amazon S3   │   │  DynamoDB    │            │
                     │  Data Lake   │   │  Metrics     │            │
                     │  (brut)      │   │  (agrégé)    │            │
                     └──────────────┘   └──────────────┘            │
                                                                    ▼
                                                           ┌──────────────┐
                                                           │  CloudFront  │
                                                           │  + OAC       │
                                                           │  (Doc)       │
                                                           └──────────────┘
```

### Services AWS utilisés
| Service | Rôle |
|---------|------|
| **AWS CloudFormation (SAM)** | Infrastructure as Code |
| **Amazon S3 (x2)** | Data Lake brut + Documentation |
| **Amazon DynamoDB** | Feature Store / Métriques agrégées |
| **AWS Lambda** | Traitement à la volée (Python 3.11) |
| **Amazon API Gateway** | Point d'entrée HTTP REST |
| **Amazon CloudFront (x2)** | CDN ingestion + CDN documentation sécurisé |
| **Amazon CloudWatch** | Logs et monitoring |
| **AWS IAM** | Gestion des permissions |

---

## 3. Infrastructure as Code (CloudFormation)

### Fichier : `infrastructure/template.yaml`

Le template SAM (Serverless Application Model) définit toutes les ressources :

#### 3.1 Buckets S3
- **`RawDataBucket`** (`${AWS::StackName}-raw-data`) : Stockage des données brutes IoT
- **`DocumentationBucket`** (`${AWS::StackName}-tech-doc`) : Hébergement du site de documentation

#### 3.2 Table DynamoDB
- **`MetricsTable`** (`${AWS::StackName}-metrics`) : Stockage des métriques agrégées
  - Clé primaire : `request_id` (String)
  - Mode facturation : PAY_PER_REQUEST

#### 3.3 Fonction Lambda
- **`IngestionFunction`** (`iot-ingestion-${Environment}`)
  - Runtime : Python 3.11
  - Handler : `src/index.handler`
  - Mémoire : 256 MB
  - Timeout : 30 secondes
  - Variables d'environnement : `S3_BUCKET`, `DYNAMODB_TABLE`
  - Policies : S3CrudPolicy + DynamoDBCrudPolicy

#### 3.4 API Gateway HTTP
- **`HttpApi`** : API HTTP (ProtocolType: HTTP)
- **`IngestionRoute`** : `POST /ingest` avec intégration Lambda proxy
- **`ApiStage`** : Stage `$default` avec AutoDeploy

#### 3.5 CloudFront Ingestion
- **`IngestionDistribution`** : Distribution CloudFront devant l'API Gateway
  - Origine : API Gateway avec CustomOriginConfig (HTTPS)
  - CachePolicyId : `4135ea2d-6df8-44a3-9df3-4b5a84be39ad` (CachingDisabled)

#### 3.6 CloudFront Documentation + OAC
- **`DocumentationOAC`** : Origin Access Control pour le bucket de documentation
  - SigningBehavior : always
  - SigningProtocol : sigv4
- **`DocumentationBucketPolicy`** : Bucket Policy autorisant uniquement CloudFront
- **`DocumentationDistribution`** : Distribution CloudFront pour le site de documentation
  - DefaultRootObject : `index.html`
  - OriginAccessControlId : référence vers l'OAC

#### 3.7 Outputs
| Output | Description |
|--------|-------------|
| `CloudFrontIngestionURL` | URL CDN pour l'ingestion IoT |
| `CloudFrontDocURL` | URL CDN pour la documentation |
| `DataLakeBucket` | Nom du bucket Data Lake |
| `DocumentationBucketName` | Nom du bucket documentation |
| `DynamoDBTable` | Nom de la table DynamoDB |
| `ApiEndpoint` | URL directe de l'API Gateway |

---

## 4. Déploiement de l'Infrastructure

### Prérequis
- AWS CLI installée et configurée
- AWS SAM CLI installée
- Python 3.11
- Permissions IAM : `cloudfront:*`, `s3:*`, `dynamodb:*`, `lambda:*`, `apigateway:*`, `iam:PassRole`, `cloudformation:*`

### Étapes de déploiement

#### 4.1 Build SAM
```bash
sam build -t infrastructure/template.yaml
```

#### 4.2 Déploiement initial
```bash
sam deploy --guided
```
Paramètres :
- Stack Name : `devoir-iot-ksenou`
- Region : `eu-west-3`
- Environment : `ksenou`
- Confirm changeset : Yes
- CAPABILITY_IAM : Yes

#### 4.3 Mise à jour de la stack
```bash
sam deploy --resolve-s3 --region eu-west-3 --stack-name devoir-iot-ksenou --template-file .aws-sam/build/template.yaml --no-fail-on-empty-changeset --parameter-overrides Environment=ksenou --capabilities CAPABILITY_IAM
```

### Résultat attendu
```
CloudFormation outputs from deployed stack
---------------------------------------------------------------------
Key                 CloudFrontIngestionURL
Value               https://xxxxxxxxxxxx.cloudfront.net

Key                 CloudFrontDocURL
Value               https://yyyyyyyyyyyy.cloudfront.net

Key                 DataLakeBucket
Value               devoir-iot-ksenou-raw-data

Key                 DocumentationBucketName
Value               devoir-iot-ksenou-tech-doc

Key                 DynamoDBTable
Value               devoir-iot-ksenou-metrics

Key                 ApiEndpoint
Value               https://xxxxxxxxxx.execute-api.eu-west-3.amazonaws.com
```

---

## 5. Code Lambda (Traitement à la volée)

### Fichier : `src/index.py`

```python
import json
import os
import uuid
import boto3
from decimal import Decimal
from datetime import datetime

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

S3_BUCKET = os.environ.get("S3_BUCKET", "default-bucket")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "default-table")


def handler(event, context):
    try:
        # 1. Parse the incoming HTTP request body
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        else:
            body = event.get("body", {})

        # 2. Generate unique request ID and timestamp
        request_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        now = datetime.utcnow()
        year = now.strftime("%Y")
        month = now.strftime("%m")

        # 3. Extract measurements list
        measurements = body.get("measurements", [])

        # 4. Save raw payload to S3 with temporal partitioning
        s3_key = f"raw-zone/year={year}/month={month}/{request_id}.json"
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=json.dumps(body, indent=2),
            ContentType="application/json",
        )

        # 5. Compute metrics
        temperatures = [
            m["temperature"]
            for m in measurements
            if "temperature" in m and isinstance(m.get("temperature"), (int, float))
        ]
        avg_temperature = round(sum(temperatures) / len(temperatures), 2) if temperatures else 0.0
        error_count = sum(
            1 for m in measurements if m.get("status", "").upper() == "ERROR"
        )

        # 6. Save execution report to DynamoDB
        table = dynamodb.Table(DYNAMODB_TABLE)
        table.put_item(
            Item={
                "request_id": request_id,
                "timestamp": timestamp,
                "s3_path": s3_key,
                "avg_temperature": Decimal(str(avg_temperature)),
                "error_count": error_count,
                "total_measurements": len(measurements),
            }
        )

        return {
            "statusCode": 201,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "message": "Ingestion successful",
                "request_id": request_id,
                "s3_path": s3_key,
                "avg_temperature": avg_temperature,
                "error_count": error_count,
            }),
        }

    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "message": "Ingestion failed",
                "error": str(e),
            }),
        }
```

### Fonctionnalités
- ✅ **Parsing JSON** du corps de la requête HTTP
- ✅ **Partitionnement temporel S3** : `raw-zone/year=YYYY/month=MM/`
- ✅ **Calcul température moyenne** des mesures valides
- ✅ **Comptage des anomalies** (status = "ERROR")
- ✅ **Écriture DynamoDB** avec Decimal pour compatibilité
- ✅ **Gestion d'erreurs** avec Stack Trace dans CloudWatch

---

## 6. Script Client de Test

### Fichier : `test_client.py`

```python
import requests
import json

# URLs from the stack Outputs
CLOUDFRONT_URL = "https://dimjaatmzzr2n.cloudfront.net"
API_URL = "https://d1ngb7eee3.execute-api.eu-west-3.amazonaws.com"

# Valid payload with 4+ structured measurements
valid_payload = {
    "measurements": [
        {"sensor_id": "sensor-001", "temperature": 22.5, "status": "OK"},
        {"sensor_id": "sensor-002", "temperature": 25.1, "status": "OK"},
        {"sensor_id": "sensor-003", "temperature": 18.3, "status": "ERROR"},
        {"sensor_id": "sensor-004", "temperature": 30.7, "status": "OK"},
        {"sensor_id": "sensor-005", "temperature": 19.8, "status": "ERROR"},
    ]
}

# Test 1: Valid payload via CloudFront
response = requests.post(f"{CLOUDFRONT_URL}/ingest", json=valid_payload, timeout=30)
print(f"Status: {response.status_code}")  # Expected: 201

# Test 2: Valid payload via API Gateway direct
response = requests.post(f"{API_URL}/ingest", json=valid_payload, timeout=30)
print(f"Status: {response.status_code}")  # Expected: 201

# Test 3: Corrupted payload (malformed JSON)
response = requests.post(
    f"{CLOUDFRONT_URL}/ingest",
    data="this is not valid json",
    headers={"Content-Type": "application/json"},
    timeout=30
)
print(f"Status: {response.status_code}")  # Expected: 400
```

### Exécution
```bash
python test_client.py
```

### Résultats attendus
- ✅ Test 1 : Status **201** — Ingestion réussie via CloudFront
- ✅ Test 2 : Status **201** — Ingestion réussie via API directe
- ✅ Test 3 : Status **400** — JSON corrompu détecté
- ✅ Test 4 : Status **201** — Températures manquantes (calcul avec 0 mesures)

---

## 7. Site de Documentation Technique

### Fichier : `index.html`

Page HTML statique contenant :
- Titre du cours : "Ingénierie Big Data & IA — Architecture Cloud AWS"
- Description complète de l'architecture déployée
- Schéma du flux de données
- Composants avec leurs rôles
- Notes de sécurité

### Upload vers S3
```bash
aws s3 cp index.html s3://devoir-iot-ksenou-tech-doc/index.html
```

### Vérification de la sécurité OAC
```bash
# Accès direct S3 → doit retourner 403 Access Denied
curl -I https://devoir-iot-ksenou-tech-doc.s3.eu-west-3.amazonaws.com/index.html

# Accès via CloudFront → doit retourner 200 OK
curl -I https://xxxxxxxxxxxx.cloudfront.net/index.html
```

---

## 8. Validation et Tests

### 8.1 Vérification S3 (Data Lake)
```bash
aws s3 ls s3://devoir-iot-ksenou-raw-data/raw-zone/year=2026/month=06/
```
Résultat : Fichier JSON présent avec le partitionnement temporel

### 8.2 Vérification DynamoDB (Métriques)
```bash
aws dynamodb scan --table-name devoir-iot-ksenou-metrics --region eu-west-3
```
Résultat : Ligne insérée avec `request_id`, `timestamp`, `s3_path`, `avg_temperature`, `error_count`

---

## 9. Monitoring et Gestion des Échecs

### 9.1 CloudWatch Logs
```bash
# Lister les groupes de logs
aws logs describe-log-groups --region eu-west-3 --log-group-name-prefix /aws/lambda/iot-ingestion

# Lire les logs d'exécution
aws logs get-log-events \
  --region eu-west-3 \
  --log-group-name /aws/lambda/iot-ingestion-ksenou \
  --log-stream-name "2026/06/09/[$LATEST]xxxxx"
```

### 9.2 Test d'échec (payload corrompu)
```bash
curl -X POST https://xxxxxxxxxxxx.cloudfront.net/ingest \
  -d "not valid json" \
  -H "Content-Type: application/json"
```
Résultat : Status **400** avec message d'erreur + Stack Trace complète dans CloudWatch

---

## 10. Réponses aux Questions Théoriques

### Question 1 : Infrastructure as Code (IaC) et CloudFormation

**L'Infrastructure as Code (IaC)** est une pratique DevOps qui consiste à gérer et provisionner l'infrastructure via des fichiers de configuration déclaratifs plutôt que par des actions manuelles. Cela permet la répétabilité, la versioning, l'automatisation et la reproductibilité des environnements.

**AWS CloudFormation** est le service IaC d'AWS qui modélise l'ensemble des ressources sous forme de template (JSON/YAML). Il gère le cycle de vie complet :
- **Création** : Provisionne les ressources dans l'ordre de dépendance
- **Mise à jour** : Modifie les ressources existantes sans downtime
- **Suppression** : Nettoie proprement toutes les ressources
- **Rollback** : Revient à l'état précédent en cas d'échec

### Question 2 : AWS Lambda vs EC2

**AWS Lambda** est un service de calcul serverless qui exécute du code en réponse à des événements, sans provisionner ni gérer de serveurs.

**Différences clés avec EC2 :**

| Critère | Lambda (Serverless) | EC2 (Instance virtuelle) |
|---------|-------------------|------------------------|
| Provisionnement | Automatique, immédiat | Manuel, plusieurs minutes |
| Facturation | À l'exécution (ms) | À l'heure (instance allumée) |
| Scalabilité | Automatique, massive | Manuelle (Auto Scaling) |
| Maintenance | AWS gère tout | OS, patches à gérer |
| Limite temps | Max 15 minutes | Illimité |
| Idéal pour | Événementiel, API, traitement rapide | Applications longues, lourdes |

### Question 3 : CloudFront devant API Gateway pour IoT

**Intérêt architectural :**
1. **Réduction de latence** : Edge locations proches des capteurs IoT mondiaux
2. **Terminaison TLS** : Sécurisation des données en transit
3. **Cache des réponses** : Réduction de la charge sur API Gateway
4. **Protection DDoS** : CloudFront absorbe les attaques volumétriques
5. **Géolocalisation** : Routage intelligent basé sur la localisation du capteur
6. **Coût réduit** : Moins d'appels à API Gateway grâce au cache

### Question 4 : S3 vs DynamoDB vs RDS pour Big Data

**Pourquoi une architecture polyglotte ?**

| Cas d'usage | Service | Justification |
|------------|---------|---------------|
| **Données brutes** (Data Lake) | **S3** | Stockage illimité, faible coût, formats variés (JSON, Parquet, CSV) |
| **Métriques agrégées** (Serving Layer) | **DynamoDB** | Latence milliseconde, scalabilité horizontale, requêtes clé-valeur rapides |
| Éviter | **RDS** unique | Goulot d'étranglement, coût élevé, pas adapté aux volumes massifs IoT |

**Principe** : Séparation des préoccupations (Separation of Concerns) : S3 pour le stockage froid/brut, DynamoDB pour l'accès chaud/analytique.

### Question 5 : Modèle de responsabilité partagée S3

Le modèle de responsabilité partagée AWS pour S3 :

**AWS est responsable de :**
- Infrastructure physique des datacenters
- Réseau, stockage, serveurs
- Durabilité des données (99.999999999%)
- Chiffrement au repos côté serveur

**Le client est responsable de :**
- Configuration des politiques d'accès (Bucket Policy, ACL)
- Gestion des clés de chiffrement (SSE-C, KMS)
- Activation de la versioning et des logs d'accès
- Blocage des accès publics (Block Public Access)
- Rotation des clés IAM utilisateurs

### Question 6 : Static Website Hosting vs CloudFront + OAC

**Pourquoi ne pas activer Static Website Hosting public ?**
1. **Bucket accessible publiquement** → n'importe qui peut lister/télécharger
2. **Pas de chiffrement TLS** par défaut (HTTP simple)
3. **Pas de protection DDoS** intégrée
4. **Pas de cache CDN** → latence élevée

**Avantages de CloudFront + OAC :**
1. **OAC (Origin Access Control)** : Seul CloudFront peut accéder au bucket S3
2. **Accès S3 direct bloqué** (Access Denied)
3. **TLS/HTTPS** intégré via CloudFront
4. **Cache CDN** mondial (faible latence)
5. **Protection DDoS** via AWS Shield Standard
6. **Géolocalisation et restrictions** possibles

### Question 7 : CloudWatch pour le débogage Serverless

**CloudWatch** permet de superviser et déboguer via :
1. **Logs** : Chaque exécution Lambda génère un log stream avec `print()`, `logging`, et les traces d'erreur
2. **Métriques** : Invocations, durée, erreurs, throttles
3. **Alertes** : Déclenchement d'actions (SNS, emails) sur seuils
4. **Traces X-Ray** : Suivi des appels entre services

**En cas d'exception non gérée :**
- Lambda écrit automatiquement la **Stack Trace Python** complète dans CloudWatch Logs
- L'exécution est marquée comme `error` dans les métriques CloudWatch
- Le log contient : type d'erreur, message, traceback complet avec numéros de ligne
- Retry automatique selon la configuration (2 fois par défaut pour les événements asynchrones)

### Question 8 : Limites Lambda pour 50 Go et alternative Big Data

**Pourquoi Lambda atteint ses limites avec 50 Go ?**
1. **Timeout max** : 15 minutes (un fichier de 50 Go nécessite bien plus)
2. **Mémoire max** : 10 Go (insuffisant pour charger 50 Go en mémoire)
3. **Temps d'exécution** : Le transfert réseau et le traitement dépassent le timeout
4. **Payload max** : 256 Ko pour les événements synchrones

**Service alternatif recommandé : AWS Glue** (ETL serverless)
- **AWS Glue** : Service ETL serverless conçu pour le Big Data
  - Pas de limite de temps (exécution longue)
  - Mémoire configurable jusqu'à plusieurs dizaines de Go
  - Optimisé pour Spark (traitement distribué)
  - Connexion native à S3, Redshift, RDS
  - Format Parquet/ORC optimisé pour les gros volumes
- **Alternative** : Amazon EMR (Elastic MapReduce) pour Spark/Hadoop

---

## 11. Captures d'Écran

*(À capturer depuis la console AWS et à insérer dans le rapport PDF)*

### 11.1 CloudFormation — Stack CREATE_COMPLETE
- Console → CloudFormation → Stacks → `devoir-iot-ksenou`
- Capturer : statut, resources, outputs

### 11.2 S3 — Data Lake avec fichiers
- Console → S3 → `devoir-iot-ksenou-raw-data`
- Naviguer : `raw-zone/year=2026/month=06/`
- Capturer : liste des fichiers JSON avec leurs dates

### 11.3 DynamoDB — Lignes insérées
- Console → DynamoDB → Tables → `devoir-iot-ksenou-metrics`
- Cliquer "Explore table items"
- Capturer : les items avec request_id, avg_temperature, error_count

### 11.4 CloudWatch Logs — Exécution réussie
- Console → CloudWatch → Log groups → `/aws/lambda/iot-ingestion-ksenou`
- Ouvrir le dernier log stream
- Capturer : le log de l'exécution 201 (sans erreur)

### 11.5 CloudWatch Logs — Stack Trace d'erreur
- Envoyer un payload corrompu
- Recharger CloudWatch Logs
- Capturer : le log avec l'erreur JSON et la Stack Trace Python

---

## 12. Livrables

Dossier compressé `.zip` contenant :

```
devoir-iot-final.zip
│
├── infrastructure/
│   └── template.yaml          # Template CloudFormation (SAM)
│
├── src/
│   └── index.py               # Code Lambda Python 3.11
│
├── test_client.py             # Script client de test
│
├── index.html                 # Page de documentation technique
│
├── README.md                  # Ce fichier (documentation complète)
│
└── Rapport.pdf                # Rapport avec captures d'écran + questions théoriques
```
