# Social Analyzer

Ferramenta de linha de comando para gerar, a partir de um `@usuário` do
Instagram ou TikTok, um **relatório em PDF de diagnóstico de redes sociais** —
pensado para ser enviado a um cliente em potencial como parte de uma
prospecção comercial (agência/freelancer de marketing/social media).

O relatório traz: seguidores, taxa de engajamento, frequência de postagem,
melhor e pior publicação recente, uma lista de pontos fortes/fracos gerada
automaticamente a partir de benchmarks de mercado, e uma seção de proposta
para acompanhamento mensal ou quinzenal contínuo.

A cada nova execução para o **mesmo cliente**, o relatório passa a mostrar
também a evolução desde a última análise (crescimento de seguidores,
variação de engajamento) — é assim que a ferramenta sustenta o
acompanhamento periódico do contrato.

## Como funciona

Os dados públicos do perfil são coletados via [Apify](https://apify.com)
(scraping de dados públicos, sem necessidade de login na conta do cliente):

- Instagram → actor `apify/instagram-profile-scraper`
- TikTok → actor `clockworks/tiktok-profile-scraper`

Isso tem um custo pequeno por execução na sua conta Apify (plano free
cobre uso moderado):
- Instagram: ~US$ 0,0026 por perfil analisado (praticamente irrelevante).
- TikTok: ~US$ 0,003 por vídeo analisado — com `--posts-limit 12` (padrão),
  cerca de US$ 0,04 por análise.

## Instalação

```bash
cd social-analyzer
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Crie uma conta gratuita em https://console.apify.com, gere um token em
**Settings → Integrations** e exporte-o:

```bash
export APIFY_API_TOKEN="seu_token_aqui"
```

## Uso

```bash
# Instagram
python cli.py --instagram nomedocliente --client "Loja da Ana" --agency "Minha Agência"

# TikTok
python cli.py --tiktok nomedocliente --client "Loja da Ana" --agency "Minha Agência"
```

O PDF é salvo em `reports/` (ex.: `reports/instagram_nomedocliente_20260818.pdf`).

### Opções

| Flag | Descrição |
|---|---|
| `--instagram USUARIO` / `--tiktok USUARIO` | @ ou URL do perfil (obrigatório escolher um) |
| `--client "Nome"` | Nome do cliente no relatório (padrão: nome do perfil) |
| `--agency "Nome"` | Nome da sua agência/empresa no relatório |
| `--posts-limit N` | Quantos posts recentes analisar (padrão: 12) |
| `--output caminho.pdf` | Caminho customizado do PDF |
| `--apify-token TOKEN` | Alternativa a definir `APIFY_API_TOKEN` |
| `--no-save` | Não grava este resultado no histórico (não conta para comparações futuras) |

## Acompanhamento mensal/quinzenal

O histórico de cada cliente fica salvo em
`data/history/<plataforma>_<usuario>.json`. Basta rodar o mesmo comando
novamente (ex. todo mês ou a cada 15 dias) — o próximo PDF gerado já traz a
comparação com a análise anterior automaticamente. **Não apague os arquivos
em `data/history/`** entre uma análise e outra do mesmo cliente.

## Estrutura

```
social-analyzer/
├── cli.py                # ponto de entrada (linha de comando)
├── src/
│   ├── scraper.py        # coleta via Apify (Instagram/TikTok) e normalização
│   ├── metrics.py        # cálculo de engajamento + geração de prós/contras
│   ├── history.py        # snapshots por cliente para comparação periódica
│   ├── charts.py         # gráficos (matplotlib) embutidos no PDF
│   └── report.py         # montagem do PDF (reportlab)
├── data/history/         # snapshots salvos por cliente (gitignored)
└── reports/               # PDFs gerados (gitignored)
```

## Limitações conhecidas

- Perfis privados não podem ser analisados (dados públicos apenas).
- Os "prós e contras" são gerados por regras/benchmarks aproximados de
  mercado — servem como ponto de partida para a conversa comercial, não
  como verdade absoluta.
- O actor do TikTok cobra por vídeo coletado; ajuste `--posts-limit` para
  controlar o custo.
