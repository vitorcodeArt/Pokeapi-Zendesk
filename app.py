import requests
from flask import Flask, request, jsonify
from base64 import b64encode
import os
import json

app = Flask(__name__)

# === CONFIGURAÇÕES ZENDESK ===
ZENDESK_SUBDOMINIO = 'conbcrcxfabio1745583316'
ZENDESK_EMAIL = 'consultoriazendesk@bcrcx.com/token'
ZENDESK_TOKEN = 'RJ2akwbMSs0BBZMqKy3j6l3ALWh00j3Dj9vgHmcv'

# IDs dos campos personalizados
ID_CAMPO_GERACAO = 37991201870491  # VM - Pokeapi
ID_CAMPO_GERACAO_1 = 38004431773211
ID_CAMPO_GERACAO_2 = 38004435047963
ID_CAMPO_GERACAO_3 = 38004428408347

CAMPOS_GERACAO = {
    "geracao_1": ID_CAMPO_GERACAO_1,
    "geracao_2": ID_CAMPO_GERACAO_2,
    "geracao_3": ID_CAMPO_GERACAO_3,
}

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

def get_cor_tipo(tipo):
    cores = {
        "normal": "#74797c", "fire": "#fd7d24", "water": "#4592c4", "grass": "#74993c",
        "electric": "#bba729", "ice": "#51c4e7", "fighting": "#d56723", "poison": "#b97fc9",
        "ground": "#ab9842", "flying": "#9aa7fa", "psychic": "#f0a7eb", "bug": "#b7c43e",
        "rock": "#c5b678", "ghost": "#7d7cc0", "dragon": "#8b7ceb", "steel": "#b7b6c0", "dark": "#8b6d5b"
    }
    return cores.get(tipo.lower(), "#ccc")

def render_tipo(tipo):
    cor = get_cor_tipo(tipo)
    return f"""
    <span style="display:inline-block; background-color:{cor}; color:#fff; padding:4px 8px; border-radius:6px; margin-right:6px; font-size:13px; font-weight:500; box-shadow:0 0 6px #00000040;">{tipo.capitalize()}</span>
    """

def atualizar_ticket(ticket_id, pokemon):
    dados = buscar_dados_pokemon(pokemon)
    if not dados:
        return False

    tipos = dados['tipos'].split(', ')
    cor_fundo = get_cor_tipo(tipos[0])
    tipos_html = ''.join(render_tipo(tipo) for tipo in tipos)

    html_body = f"""
    <div style="border: 1px solid #ccc; border-radius: 10px; padding: 16px; background-color: #f9f9f9; max-width: 300px; min-width: 300px;">
        <p style="margin: 0 0 10px 0; font-size: 1.2rem;">
            {dados['nome'].capitalize()}
        </p>
        <p style="margin: 0 0 10px 0;">
            {tipos_html}
        </p>
        <div class="fundo" style="text-align: center; height: 130px; display: flex; justify-content: center; border-radius: 16px; background: linear-gradient(145deg, {cor_fundo}50, transparent); padding: 12px;">
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

    print("Recebido webhook JSON:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    ticket_id = data.get('ticket_event', {}).get('ticket', {}).get('id')
    if not ticket_id:
        return jsonify({"error": "ID do ticket não encontrado"}), 400

    # Requisição para buscar o ticket completo via API
    url = f"https://{ZENDESK_SUBDOMINIO}.zendesk.com/api/v2/tickets/{ticket_id}.json"
    res = requests.get(url, headers=get_auth_header())
    if res.status_code != 200:
        return jsonify({"error": "Falha ao buscar ticket completo"}), 400

    ticket = res.json().get("ticket", {})
    campos_customizados = ticket.get("custom_fields", [])

    print("Campos customizados recebidos:")
    print(json.dumps(campos_customizados, indent=2, ensure_ascii=False))

    # Extrair a geração correta (remover "pokeapi_" do início)
    geracao_selecionada = None
    for campo in campos_customizados:
        if campo.get('id') == ID_CAMPO_GERACAO:
            valor = campo.get('value')
            if valor and valor.startswith("pokeapi_"):
                geracao_selecionada = valor.replace("pokeapi_", "")
            else:
                geracao_selecionada = valor
            break

    print(f"Geração selecionada: {geracao_selecionada}")

    # Obter ID do campo de Pokémon conforme a geração
    id_campo_pokemon = CAMPOS_GERACAO.get(geracao_selecionada)
    pokemon = None

    if id_campo_pokemon:
        for campo in campos_customizados:
            if campo.get('id') == id_campo_pokemon:
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
