# Mostra Científica — Rede Municipal de Ensino de Caxias do Sul (Edição 2026)

Site estático (HTML/CSS/JS puro, sem build) para divulgação da Mostra Científica.

## Estrutura

```
.
├── index.html                     # Página inicial
├── edital.html                    # Edital e documentos oficiais
├── inscricoes.html                # Formulário e passo a passo de inscrição
├── inscricoes-homologadas.html    # Lista de projetos homologados
├── cronograma.html                # Linha do tempo com as datas do evento
├── localizacao.html               # Endereço e mapa do local
├── fotos.html                     # Galeria de fotos
├── contato.html                   # Formulário e dados de contato
└── assets/
    ├── css/style.css
    ├── js/main.js
    └── img/
```

## Como visualizar localmente

Basta abrir `index.html` no navegador, ou rodar um servidor estático:

```bash
python3 -m http.server 8000
# acesse http://localhost:8000
```

## Pendências para publicação (marcadas no conteúdo com `[Inserir ...]`)

- Substituir o logo recriado em SVG pelo arquivo oficial da marca (`assets/img/`).
- Preencher datas reais no Cronograma e na Home.
- Anexar os PDFs oficiais na página de Edital (links `href="#"`).
- Definir o endereço real do evento e atualizar o `src` do `iframe` do Google Maps em `localizacao.html`.
- Substituir os placeholders da galeria em `fotos.html` por fotos reais.
- Conectar os formulários de Inscrição e Contato a um serviço de envio real (Formspree, EmailJS, backend próprio, etc.), pois atualmente funcionam apenas no front-end.
- Atualizar a lista de Inscrições Homologadas com os dados reais.

## Hospedagem

Por ser um site 100% estático, pode ser publicado em qualquer serviço de hospedagem estática, como GitHub Pages, Netlify ou Vercel.
