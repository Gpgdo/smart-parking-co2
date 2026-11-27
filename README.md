# Smart Parking CO₂

## 👥 Integrantes
- Gabriel Pereira Gil de Oliveira — integrante da dupla
- Guilherme Gonçalves Hermano — integrante da dupla

Projetos em Engenharia da Computação I · Universidade do Vale do Paraíba (Univap)
Orientador: Prof. Hélio Esperidião

## 📌 Descrição
Analisador de ocupação de ambientes fechados por sinais de CO₂. O sistema aplica Processamento Digital
de Sinais a um **dataset público real** de uma sala de escritório (20.560 leituras em 17 dias). Ele filtra o
sinal, detecta picos, calcula média, mediana e desvio padrão em janelas de 1 hora, agrupa as janelas com
K-means e compara os resultados com a ocupação real em um dashboard web.

> **Atualização:** o projeto começou com um simulador (fluxo de veículos +
> sensor virtual de CO₂), mas a pedido da disciplina passou a usar dados
> **reais**: o dataset "Occupancy Detection" (CANDANEDO; FELDHEIM, 2016), com
> CO₂ e ocupação medidos de verdade em uma sala fechada, minuto a minuto. Não
> encontramos dataset público de CO₂ dentro de um estacionamento real, então
> usamos o dataset real mais próximo do mesmo princípio físico (CO₂ como
> indicador indireto de ocupação/movimentação em ambiente fechado). O
> simulador antigo continua no repo como referência ([src/simulation.py](src/simulation.py)),
> mas não faz mais parte do pipeline ativo.

## 🛠️ Tecnologias
- Frontend: HTML, CSS, JavaScript e Chart.js
- Backend: Python, FastAPI, Uvicorn, pandas, NumPy, SciPy, scikit-learn, Matplotlib, Psycopg e python-dotenv
- Banco de dados: PostgreSQL 16 (Docker Compose)

## ⚙️ Como executar

Pré-requisitos: Python (o projeto foi desenvolvido com Python 3.14) e Docker Desktop aberto.
Os comandos são para o PowerShell, **um por vez**.

1. Clone o repositório:

```powershell
git clone https://github.com/Gpgdo/smart-parking-co2.git
```

```powershell
cd smart-parking-co2
```

2. Crie o ambiente e instale as dependências:

```powershell
python -m venv .venv
```

```powershell
.venv\Scripts\pip install -r requirements.txt
```

3. Configure o `.env` (os valores do exemplo funcionam com o Docker Compose):

```powershell
copy .env.example .env
```

4. Suba o banco e importe os dados:

```powershell
docker compose up -d --wait
```

```powershell
docker cp db\dump\smart_parking_dump.sql smart_parking_postgres:/tmp/backup.sql
```

```powershell
docker exec smart_parking_postgres psql -U parking -d smart_parking -v ON_ERROR_STOP=1 -f /tmp/backup.sql
```

5. Rode o projeto:

```powershell
.venv\Scripts\uvicorn api.main:app --reload
```

Abra http://localhost:8000. A documentação da API fica em http://localhost:8000/docs (precisa de internet).
Para encerrar: `Ctrl+C` e depois `docker compose down`.

### Alternativa: gerar os dados pelo pipeline

Em vez de importar o backup (passo 4), suba o banco e rode:

```powershell
.venv\Scripts\python src\load_real_data.py
```

```powershell
.venv\Scripts\python src\signal_processing.py
```

```powershell
.venv\Scripts\python src\load_to_db.py
```

### Reprocessando pelo próprio dashboard

Em vez de rodar os três scripts manualmente, dá para clicar em
**"🔄 Reprocessar dataset real"** no topo do dashboard: a API roda o pipeline
inteiro (`load_real_data.py` → `signal_processing.py` → `load_to_db.py`) no
servidor e a página recarrega sozinha. Como o dataset agora é real e fixo
(não é mais gerado aleatoriamente), o resultado é sempre o mesmo — o botão
serve para demonstrar o pipeline rodando ao vivo, sem precisar de terminal.

## 🗄️ Banco de dados
Instruções em [db/instrucoes-banco.md](db/instrucoes-banco.md).

| Arquivo | Conteúdo |
|---|---|
| [db/schema.sql](db/schema.sql) | Criação das tabelas e índices |
| [db/seed.sql](db/seed.sql) | Dados iniciais |
| [db/dump/smart_parking_dump.sql](db/dump/smart_parking_dump.sql) | Backup completo |
| [db/diagrama-er.png](db/diagrama-er.png) | Diagrama ER |

As tabelas são `parking_readings` (20.560 leituras) e `co2_peaks` (30 picos).

## 📚 Referências
Ver [referencias/referencias-abnt.pdf](referencias/referencias-abnt.pdf) e
[referencias/links-consultados.md](referencias/links-consultados.md). A lista também está em
[REFERENCIAS.md](REFERENCIAS.md).

## 📖 Manual de uso
[docs/manual-de-uso.pdf](docs/manual-de-uso.pdf)

## 🔗 Repositório
https://github.com/Gpgdo/smart-parking-co2

## Dashboard

![Dashboard do Smart Parking CO2 com cards de resumo, grafico de CO2 do periodo, detalhe por dia com picos, estatistica basica em janelas de 1 hora (media, mediana e desvio padrao), agrupamento K-means das janelas, comparativo de ocupacao real x atividade estimada por dia da semana e tabela de picos](docs/dashboard.png)

*Dashboard rodando com o dataset real (20.560 leituras, 30 picos de CO₂, 17 dias entre 02/02/2015 e 18/02/2015).*

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
   `/api/*` (leituras, picos, estatísticas por dia e por hora, agrupamento
   K-means, resumo geral) e também serve o dashboard.
5. **Dashboard Web ([web/](web))** — página estática (HTML/CSS/JS + Chart.js)
   que consome a API e mostra:
   - gráficos de CO₂ (bruto × filtrado) e detalhe por dia, com os picos;
   - **estatística básica em janelas de 1 hora** (média, mediana e desvio
     padrão do CO₂, calculados no PostgreSQL), com seletor de dia (os 17 dias
     coletados ou "todos os dias");
   - **agrupamento K-means** ([src/clustering.py](src/clustering.py), scikit-learn)
     das janelas de 1 hora em 2 ou 3 grupos, com a silhouette e a comparação
     de cada grupo com a ocupação real;
   - comparativo ocupação real × atividade estimada pelo CO₂ por dia da semana.

Fonte do dataset: CANDANEDO, L. M.; FELDHEIM, V. *Accurate occupancy
detection of an office room from light, temperature, humidity and CO2
measurements using statistical learning models*. Energy and Buildings,
v. 112, p. 28-39, 2016.

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
| GET    | `/api/stats/hourly`    | Média, mediana e desvio padrão do CO₂ em janelas de 1 hora (`?dia=YYYY-MM-DD`) |
| GET    | `/api/clusters`        | K-means (scikit-learn) sobre as janelas de 1 hora (`?k=2` a `4`, padrão 3) |
| POST   | `/api/simulate`        | Roda o pipeline completo e recarrega os dados no banco  |

## Estrutura do projeto

```
smart-parking-co2/
├── src/
│   ├── load_real_data.py     # baixa e prepara o dataset real de CO2/ocupação
│   ├── signal_processing.py  # filtro, detecção de picos, análise por dia
│   ├── clustering.py         # K-means das janelas de 1 hora (scikit-learn)
│   ├── db.py                 # conexão com o PostgreSQL
│   ├── load_to_db.py         # carga dos CSVs processados no banco
│   └── simulation.py         # LEGADO: simulador sintético (não é mais usado)
├── db/
│   ├── schema.sql            # schema das tabelas
│   ├── seed.sql              # dados iniciais (INSERTs)
│   ├── diagrama-er.png       # diagrama entidade-relacionamento
│   ├── instrucoes-banco.md   # como importar o banco
│   └── dump/                 # backup do banco (pg_dump) com os dados reais
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
├── referencias/              # referências em PDF (ABNT) e links consultados
├── docs/                     # manual de uso (PDF) e imagem do dashboard
├── REFERENCIAS.md            # referências (ABNT)
├── requirements.txt
└── .env.example
```

## Solução de problemas

- **`/api/health` retorna 503 / dashboard mostra erro** → o Postgres não
  está rodando ou o banco ainda não foi populado. Rode `docker compose ps`
  para conferir o container e, se preciso, refaça o passo 4.
- **Acentos/caracteres estranhos no terminal** → é só a exibição no console
  do Windows (cp1252); os arquivos CSV e o banco continuam corretos em
  UTF-8.
