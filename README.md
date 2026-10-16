# Smart Parking CO₂

Analisador de Ocupação por Sinais de CO₂ utilizando Processamento Digital de
Sinais, aplicado a um **dataset público real** (não mais simulado).

> **Atualização:** o projeto começou com um simulador (fluxo de veículos +
> sensor virtual de CO₂), mas a pedido da disciplina passou a usar dados
> **reais**: o dataset "Occupancy Detection" (CANDANEDO; FELDHEIM, 2016), com
> CO₂ e ocupação medidos de verdade em uma sala fechada, minuto a minuto. Não
> existe dataset público de CO₂ dentro de um estacionamento real, então
> usamos o dataset real mais próximo do mesmo princípio físico (CO₂ como
> indicador indireto de ocupação/movimentação em ambiente fechado). O
> simulador antigo continua no repo como referência ([src/simulation.py](src/simulation.py)),
> mas não faz mais parte do pipeline ativo.

```
Dataset real de CO₂/ocupação (UCI/Candanedo & Feldheim, 2016)
          ↓
Processamento de sinais em Python
          ↓
PostgreSQL
          ↓
API (FastAPI)
          ↓
Dashboard Web
```

## Dashboard

![Dashboard do Smart Parking CO2, mostrando os cards de resumo (leituras processadas, minutos ocupados, CO2 medio e maximo, picos detectados, dia de maior ocupacao real e dia de maior atividade estimada pelo CO2), o grafico de CO2 no periodo do dataset real, o detalhe por dia com os picos marcados, e o comparativo de ocupacao real x atividade estimada por dia da semana ao lado da tabela de picos detectados](docs/dashboard.png)

*Dashboard rodando com o dataset real (20.560 leituras, 30 picos de CO₂ detectados, 17 dias entre 02/02/2015 e 18/02/2015).*

## Como funciona

1. **Carga do dataset real ([src/load_real_data.py](src/load_real_data.py))**
   — baixa (uma vez) e lê os 3 arquivos do dataset público
   [Occupancy Detection](https://github.com/LuisM78/Occupancy-detection-data)
   (CO₂, temperatura, umidade, luz e ocupação real 0/1, ~20.560 amostras a
   cada ~1 minuto, coletados em fevereiro de 2015).
2. **Processamento de sinais ([src/signal_processing.py](src/signal_processing.py))**
   — aplica um filtro de média móvel para suavizar o sinal real de CO₂
   (`co2_filtered`), detecta picos de concentração (`scipy.signal.find_peaks`)
   e calcula um índice de atividade por dia da semana, comparando a
   estimativa feita a partir do CO₂ com a **ocupação real** (minutos ocupados,
   medidos por foto no dataset original).
3. **PostgreSQL** — os resultados processados são carregados na tabela
   `parking_readings` (leituras) e `co2_peaks` (picos) por
   [src/load_to_db.py](src/load_to_db.py).
4. **API ([api/main.py](api/main.py))** — FastAPI expõe os dados do banco em
   `/api/*` (leituras, picos, estatísticas por dia, resumo geral) e também
   serve o dashboard.
5. **Dashboard Web ([web/](web))** — página estática (HTML/CSS/JS + Chart.js)
   que consome a API e mostra gráficos de CO₂, atividade por dia e picos
   detectados.

Fonte do dataset: CANDANEDO, L. M.; FELDHEIM, V. *Accurate occupancy
detection of an office room from light, temperature, humidity and CO2
measurements using statistical learning models*. Energy and Buildings,
v. 112, p. 28-39, 2016.

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

### 4. Rodar o pipeline (dataset real → processamento → banco)

```bash
.venv\Scripts\python src\load_real_data.py
.venv\Scripts\python src\signal_processing.py
.venv\Scripts\python src\load_to_db.py
```

- `load_real_data.py` baixa (se preciso) os arquivos brutos em `data/raw/` e
  gera `data/co2_real_dataset.csv`
- `signal_processing.py` gera `data/processed_real_dataset.csv`,
  `data/co2_peaks.csv` e os gráficos em `charts/`
- `load_to_db.py` garante o schema no Postgres e carrega os dois CSVs nas
  tabelas `parking_readings` e `co2_peaks`

### 5. Rodar a API + Dashboard

```bash
.venv\Scripts\uvicorn api.main:app --reload
```

Abra **http://localhost:8000** no navegador para ver o dashboard.
A documentação interativa da API fica em **http://localhost:8000/docs**.

### Reprocessando pelo próprio dashboard

Em vez de rodar os três scripts manualmente (passo 4), dá para clicar em
**"🔄 Reprocessar dataset real"** no topo do dashboard: a API roda o pipeline
inteiro (`load_real_data.py` → `signal_processing.py` → `load_to_db.py`) no
servidor e a página recarrega sozinha. Como o dataset agora é real e fixo
(não é mais gerado aleatoriamente), o resultado é sempre o mesmo — o botão
serve para demonstrar o pipeline rodando ao vivo, sem precisar de terminal.

## Endpoints da API

| Método | Rota                  | Descrição                                             |
|--------|-----------------------|--------------------------------------------------------|
| GET    | `/api/health`          | Verifica se a API e o banco estão disponíveis          |
| GET    | `/api/readings`        | Lista leituras (`?dia=YYYY-MM-DD` ou `?limite=N`)       |
| GET    | `/api/readings/latest` | Última leitura registrada                               |
| GET    | `/api/readings/days`   | Lista os dias disponíveis no banco                      |
| GET    | `/api/peaks`           | Lista os picos de CO₂ detectados                        |
| GET    | `/api/stats/daily`     | Ocupação real x atividade estimada por dia da semana    |
| GET    | `/api/stats/summary`   | Resumo geral (médias, máximos, dia de maior atividade)  |
| POST   | `/api/simulate`        | Roda o pipeline completo e recarrega os dados no banco  |

## Estrutura do projeto

```
smart-parking-co2/
├── src/
│   ├── load_real_data.py     # baixa e prepara o dataset real de CO2/ocupação
│   ├── signal_processing.py  # filtro, detecção de picos, análise por dia
│   ├── db.py                 # conexão com o PostgreSQL
│   ├── load_to_db.py         # carga dos CSVs processados no banco
│   └── simulation.py         # LEGADO: simulador sintético (não é mais usado)
├── db/
│   └── schema.sql            # schema das tabelas
├── api/
│   └── main.py               # API FastAPI + serve o dashboard
├── web/
│   ├── index.html
│   ├── style.css
│   └── app.js                # dashboard (fetch na API + Chart.js)
├── data/
│   ├── raw/                  # arquivos brutos do dataset real (baixados 1x)
│   └── *.csv                 # CSVs gerados pelo pipeline
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
