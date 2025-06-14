import requests
from flask import Flask, request, jsonify
from base64 import b64encode
import os
import json  # para imprimir JSON legível

app = Flask(__name__)

# === CONFIGURAÇÕES ZENDESK ===
ZENDESK_SUBDOMINIO = 'conbcrcxfabio1745583316'
ZENDESK_EMAIL = 'consultoriazendesk@bcrcx.com/token'
ZENDESK_TOKEN = 'RJ2akwbMSs0BBZMqKy3j6l3ALWh00j3Dj9vgHmcv'
CAMPO_CUSTOM_POKEMON = 'custom_fields_37991201870491'  # ID do campo personalizado

def get_auth_header():
    auth = b64encode(f"{ZENDESK_EMAIL}:{ZENDESK_TOKEN}".encode()).decode()
    return {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }

def buscar_dados_pokemon(nome):
    url = f'https://pokeapi.co/api/v2/pokemon/{nome.lower()}'
    res = requests.get(url)
    if res.status_code != 200:
        return None
    dados = res.json()
    return {
        "nome": dados['name'],
        "tipos": ', '.join(t['type']['name'] for t in dados['types']),
        "imagem": dados['sprites']['other']['showdown']['front_default']
    }

def render_tipo(tipo):
    return f"""
    <span style="
        display:inline-block;
        background-color:#eee;
        color:#333;
        padding:4px 8px;
        border-radius:6px;
        margin-right:6px;
        font-size:13px;
        font-weight:500;
        box-shadow:0 0 6px #00000040;
    ">
        {tipo}
    </span>
    """

def atualizar_ticket(ticket_id, pokemon):
    dados = buscar_dados_pokemon(pokemon)
    if not dados:
        return False

    # Gera os spans dos tipos com estilo inline
    tipos_html = ''.join(render_tipo(tipo) for tipo in dados['tipos'].split(', '))

    # Corpo do comentário em HTML com CSS inline
    html_body = f"""
    <div style="
        border: 1px solid #ccc;
        border-radius: 10px;
        padding: 16px;
        background-color: #f9f9f9;
        font-family: Arial, sans-serif;
        max-width: 300px;
    ">
        <p style="margin: 0 0 10px 0;">
            <strong style="font-size: 16px; color: #333;">Nome:</strong>
            {dados['nome'].capitalize()}
        </p>
        <p style="margin: 0 0 10px 0;">
            <strong style="font-size: 16px; color: #333;">Tipo(s):</strong><br />
            {tipos_html}
        </p>
        <div style="text-align: center;">
            <img src="{dados['imagem']}" alt="{dados['nome']}" style="max-width: 100px; margin-top: 10px;" />
        </div>
    </div>
"""
    payload = {
        "ticket": {
            "comment": {
                "html_body": html_body,
                "public": True
            },
            "tags": ["-teste_pokeapi"]
        }
    }
    url = f"https://{ZENDESK_SUBDOMINIO}.zendesk.com/api/v2/tickets/{ticket_id}.json"
    res = requests.put(url, headers=get_auth_header(), json=payload)
    return res.status_code in [200, 201]

@app.route('/webhook-pokeapi', methods=['POST'])
def receber_webhook():
    data = request.json
    
    # LOG: mostrar o JSON recebido, formatado
    print("Recebido webhook JSON:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    ticket = data.get('ticket_event', {}).get('ticket', {})
    
    campos_customizados = ticket.get('custom_fields', [])
    print("Campos customizados recebidos:")
    print(json.dumps(campos_customizados, indent=2, ensure_ascii=False))
    
    pokemon = None
    for campo in campos_customizados:
        if campo.get('id') == int(CAMPO_CUSTOM_POKEMON.replace('custom_fields_', '')):
            pokemon_raw = campo.get('value')
            if pokemon_raw and pokemon_raw.startswith("pokeapi_"):
                pokemon = pokemon_raw[len("pokeapi_"):]
            else:
                pokemon = pokemon_raw
            break

    print(f"Valor extraído do campo Pokémon: {pokemon}")

    ticket_id = ticket.get('id')
    if not ticket_id or not pokemon:
        return jsonify({"error": "ID do ticket ou pokémon não encontrado"}), 400

    sucesso = atualizar_ticket(ticket_id, pokemon)
    return jsonify({"status": "sucesso" if sucesso else "erro ao atualizar o ticket"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
