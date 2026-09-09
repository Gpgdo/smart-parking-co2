# Smart Parking CO₂

Simulador e Analisador de Estacionamento Inteligente utilizando Processamento
Digital de Sinais.

```
Simulador de estacionamento
          ↓
Sensor virtual de CO₂
          ↓
Processamento de sinais em Python
          ↓
PostgreSQL
          ↓
API (FastAPI)
          ↓
Dashboard Web
```

## Como funciona

1. **Simulador ([src/simulation.py](src/simulation.py))** — gera uma semana
   inteira (7 dias, 1 amostra/minuto) de fluxo de veículos em um
   estacionamento, com padrões de pico (manhã/almoço/final de tarde) e um
   fator diferente por dia da semana (sexta mais cheia, domingo mais vazio).
2. **Sensor virtual de CO₂** — a partir do fluxo de veículos, simula o
   acúmulo de CO₂ no ambiente (emissão por veículo + ventilação natural) e
   adiciona ruído gaussiano para imitar um sensor real (`co2_sensor`).
3. **Processamento de sinais ([src/signal_processing.py](src/signal_processing.py))**
   — aplica um filtro de média móvel para remover o ruído (`co2_filtered`),
   detecta picos de concentração (`scipy.signal.find_peaks`) e calcula um
   índice de atividade por dia da semana, comparando a estimativa feita a
   partir do CO₂ com a movimentação real simulada.
4. **PostgreSQL** — os resultados processados são carregados em duas tabelas
   (`parking_readings` e `co2_peaks`) por [src/load_to_db.py](src/load_to_db.py).
5. **API ([api/main.py](api/main.py))** — FastAPI expõe os dados do banco em
   `/api/*` (leituras, picos, estatísticas por dia, resumo geral) e também
   serve o dashboard.
6. **Dashboard Web ([web/](web))** — página estática (HTML/CSS/JS + Chart.js)
   que consome a API e mostra gráficos de CO₂, atividade por dia e picos
   detectados.

## Pré-requisitos

- Python 3.11+ (o projeto usa o `.venv` já criado, com Python 3.14)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) — para
  rodar o PostgreSQL sem precisar instalar nada manualmente

## Passo a passo (Windows / PowerShell)

### 1. Instalar as dependências Python

```bash
.venv\Scripts\pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

```bash
copy .env.example .env
```

(os valores padrão já funcionam com o `docker-compose.yml` deste projeto)

### 3. Subir o PostgreSQL

```bash
docker compose up -d
```

Isso cria um container Postgres na porta `5432` e já executa
[db/schema.sql](db/schema.sql) automaticamente na primeira inicialização.

### 4. Rodar o pipeline (simulação → processamento → banco)

```bash
.venv\Scripts\python src\simulation.py
.venv\Scripts\python src\signal_processing.py
.venv\Scripts\python src\load_to_db.py
```

- `simulation.py` gera `data/simulation.csv` e `charts/co2_week.png`
- `signal_processing.py` gera `data/processed_simulation.csv`,
  `data/co2_peaks.csv` e os gráficos em `charts/`
- `load_to_db.py` garante o schema no Postgres e carrega os dois CSVs nas
  tabelas `parking_readings` e `co2_peaks`

### 5. Rodar a API + Dashboard

```bash
.venv\Scripts\uvicorn api.main:app --reload
```

Abra **http://localhost:8000** no navegador para ver o dashboard.
A documentação interativa da API fica em **http://localhost:8000/docs**.

## Endpoints da API

| Método | Rota                  | Descrição                                             |
|--------|-----------------------|--------------------------------------------------------|
| GET    | `/api/health`          | Verifica se a API e o banco estão disponíveis          |
| GET    | `/api/readings`        | Lista leituras (`?dia=YYYY-MM-DD` ou `?limite=N`)       |
| GET    | `/api/readings/latest` | Última leitura registrada                               |
| GET    | `/api/readings/days`   | Lista os dias disponíveis no banco                      |
| GET    | `/api/peaks`           | Lista os picos de CO₂ detectados                        |
| GET    | `/api/stats/daily`     | Movimentação real x atividade estimada por dia da semana|
| GET    | `/api/stats/summary`   | Resumo geral (médias, máximos, dia de maior atividade)  |

## Estrutura do projeto

```
smart-parking-co2/
├── src/
│   ├── simulation.py         # simulador + sensor virtual de CO2
│   ├── signal_processing.py  # filtro, detecção de picos, análise por dia
│   ├── db.py                 # conexão com o PostgreSQL
│   └── load_to_db.py         # carga dos CSVs processados no banco
├── db/
│   └── schema.sql            # schema das tabelas
├── api/
│   └── main.py               # API FastAPI + serve o dashboard
├── web/
│   ├── index.html
│   ├── style.css
│   └── app.js                # dashboard (fetch na API + Chart.js)
├── data/                     # CSVs gerados pelo pipeline
├── charts/                   # gráficos .png gerados pelo pipeline
├── docker-compose.yml        # container do PostgreSQL
├── requirements.txt
└── .env.example
```

## Rodando de novo com dados novos

Basta repetir os passos 4 e 5 — cada execução de `load_to_db.py` limpa e
recarrega as tabelas, então não há duplicação.

## Solução de problemas

- **`/api/health` retorna 503 / dashboard mostra erro** → o Postgres não
  está rodando ou o banco ainda não foi populado. Rode `docker compose ps`
  para conferir o container e, se preciso, refaça o passo 4.
- **Acentos/caracteres estranhos no terminal** → é só a exibição no console
  do Windows (cp1252); os arquivos CSV e o banco continuam corretos em
  UTF-8.
