# Stock Web Scraper — Carteira do Ibovespa

Projeto em Python que coleta a carteira diária do Ibovespa diretamente de uma
fonte pública da B3, transforma os dados em um `DataFrame`, permite consultar
uma ação pelo ticker e exporta os resultados tratados para CSV e Excel.

O projeto foi desenvolvido com foco em um processo seletivo de estágio:
funções pequenas, responsabilidades separadas, tratamento de erros e decisões
técnicas fáceis de explicar em uma entrevista.

## Objetivo

Demonstrar conhecimentos de:

- requisições HTTP com `requests`;
- inspeção de uma página e consumo do endpoint usado por ela;
- validação de respostas JSON;
- limpeza e tipagem de dados com `pandas`;
- consulta e ranking de ações;
- exportação para CSV e XLSX;
- testes unitários sem dependência da internet.

## Fonte dos dados

A fonte é a [carteira diária do Ibovespa publicada pela B3](https://sistemaswebb3-listados.b3.com.br/indexPage/day/IBOV?language=pt-br).

A página é uma aplicação web. A tabela visível não vem pronta no HTML: o
JavaScript da própria página chama um endpoint público do mesmo domínio e
recebe JSON. O módulo `src/scraper.py` reproduz essa requisição `GET` com
`requests`, sem navegador automatizado, login, CAPTCHA ou mecanismo para
contornar bloqueios.

O endpoint fornece os seguintes dados usados pelo projeto:

- ticker;
- nome resumido do ativo;
- tipo e classe da ação;
- quantidade teórica na carteira;
- participação percentual no Ibovespa;
- data de referência da carteira.

O scraper faz poucas requisições, usa timeout e identifica o projeto no
`User-Agent`. Use os dados de forma educacional e consulte os termos da B3
antes de adaptar o projeto para uso frequente ou comercial.

## Tecnologias

- Python 3.10+
- requests
- pandas
- openpyxl
- pytest

BeautifulSoup não é necessário porque a fonte já entrega dados estruturados em
JSON. Fazer parsing do HTML não acrescentaria informação e tornaria o projeto
mais frágil.

## Arquitetura

```text
stock-web-scraper/
├── src/
│   ├── __init__.py
│   ├── scraper.py
│   ├── data_processing.py
│   ├── analysis.py
│   └── main.py
├── data/
│   ├── raw/
│   └── processed/
├── tests/
├── .gitignore
├── requirements.txt
├── README.md
└── LICENSE
```

- `scraper.py`: faz somente a comunicação HTTP e valida a estrutura mínima da
  resposta.
- `data_processing.py`: cria o DataFrame, limpa textos e converte números no
  formato brasileiro.
- `analysis.py`: consulta tickers, calcula destaques e produz rankings.
- `main.py`: coordena o fluxo, exibe mensagens no terminal e salva os arquivos.
- `tests/`: testa cada camada com dados controlados; a camada HTTP usa uma
  sessão falsa e não chama a B3.

## Fluxo da aplicação

```text
HTTP Request (B3)
        ↓
JSON bruto em data/raw
        ↓
Validação e parsing
        ↓
pandas DataFrame
        ↓
Limpeza e conversão de tipos
        ↓
Consulta e análise por ticker
        ↓
CSV e XLSX em data/processed
```

## Instalação no Windows

Abra o PowerShell e entre na pasta do projeto:

```powershell
cd C:\Users\Lucas\Documents\stock-web-scraper
```

Crie o ambiente virtual, caso ainda não exista:

```powershell
py -m venv .venv
```

Ative o ambiente:

```powershell
.\.venv\Scripts\Activate.ps1
```

Se o PowerShell bloquear a ativação, é possível executar o Python do ambiente
diretamente, sem alterar a política do sistema:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Instale as dependências:

```powershell
python -m pip install -r requirements.txt
```

## Como executar

Modo interativo:

```powershell
python -m src.main
```

A aplicação coleta e exporta os dados, mostra um resumo e pede um ticker, por
exemplo `PETR4`, `VALE3` ou `ITUB4`.

Também é possível informar o ticker na própria linha de comando:

```powershell
python -m src.main --ticker PETR4
```

Exemplo resumido de saída:

```text
Coletando a carteira do Ibovespa na B3...
Tratando os dados com pandas...

Resumo da carteira
Data de referência: 21/09/2026
Quantidade de ativos: 76
Maior participação: VALE3 (...%)

Ação encontrada
Ticker: PETR4
Nome: PETROBRAS
Tipo: PN N2
Quantidade teórica: ...
Participação no Ibovespa: ...%
```

Os valores mudam quando a B3 atualiza a carteira. Por isso, o exemplo não fixa
números que podem ficar desatualizados.

## Arquivos exportados

- `data/raw/ibov_carteira_bruta_AAAAMMDD_HHMMSS.json`: resposta original para
  rastreabilidade.
- `data/processed/ibov_carteira_tratada_AAAAMMDD.csv`: dados tratados em UTF-8.
- `data/processed/ibov_carteira_tratada_AAAAMMDD.xlsx`: planilha com filtro,
  cabeçalho congelado e larguras ajustadas.

Os arquivos gerados são ignorados pelo Git para evitar commits de dados que
mudam diariamente. Os diretórios permanecem no repositório por meio de
arquivos `.gitkeep`.

## Testes

Execute:

```powershell
python -m pytest -v
```

Os testes cobrem paginação do scraper, conversão de números brasileiros,
limpeza do DataFrame, consulta de ticker inexistente e rankings.

## Limitações

- A carteira cobre os ativos do Ibovespa, não todas as ações listadas na B3.
- A fonte escolhida não fornece preço, abertura, máxima, mínima, variação ou
  volume. O projeto não inventa nem estima esses campos.
- O endpoint é usado pela página pública da B3, mas não é apresentado como uma
  API pública versionada. Uma mudança na página pode exigir atualização do
  scraper; por isso há validação explícita da estrutura.
- Os dados são informativos e não constituem recomendação de investimento.

## Possíveis melhorias

- adicionar comparação entre vários tickers;
- gerar rankings configuráveis pelo terminal;
- manter um histórico local das carteiras para analisar mudanças ao longo do
  tempo;
- adicionar uma segunda fonte pública e autorizada para preços históricos;
- criar integração contínua para executar os testes automaticamente.

## Sequência sugerida de commits

```text
chore: initialize project structure
feat: implement B3 portfolio scraper
feat: add data cleaning pipeline
feat: add stock analysis and terminal interface
feat: add csv and excel export
test: add unit tests for scraper and analysis
docs: add project documentation
```

Nenhum `git push` é executado pelo projeto.

## Licença

Este projeto está disponível sob a licença MIT. Consulte o arquivo `LICENSE`.
