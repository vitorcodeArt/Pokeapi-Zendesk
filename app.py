import requests
from flask import Flask, request, jsonify
from base64 import b64encode

app = Flask(__name__)

# === CONFIGURAÇÕES ZENDESK ===
ZENDESK_SUBDOMINIO = 'conbcrcxfabio1745583316'
ZENDESK_EMAIL = 'consultoriazendesk@bcrcx.com/token'
ZENDESK_TOKEN = 'RJ2akwbMSs0BBZMqKy3j6l3ALWh00j3Dj9vgHmcv'
CAMPO_CUSTOM_POKEMON = 'custom_fields_37991201870491'  # Substitua pelo ID real do campo dropdown de Pokémon

# === AUTENTICAÇÃO ===
def get_auth_header():
    auth = b64encode(f"{ZENDESK_EMAIL}:{ZENDESK_TOKEN}".encode()).decode()
    return {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }

# === POKÉAPI ===
def buscar_dados_pokemon(nome):
    url = f'https://pokeapi.co/api/v2/pokemon/{nome.lower()}'
    res = requests.get(url)

    if res.status_code != 200:
        return None

    dados = res.json()
    return {
        "nome": dados['name'],
        "tipos": ', '.join(t['type']['name'] for t in dados['types']),
        "imagem": dados['sprites']['front_default']
    }

# === ATUALIZAÇÃO DO TICKET ===
def atualizar_ticket(ticket_id, pokemon):
    dados = buscar_dados_pokemon(pokemon)
    if not dados:
        return False

    html_body = (
        f"<p><strong>Nome:</strong> {dados['nome'].capitalize()}</p>"
        f"<p><strong>Tipo(s):</strong> {dados['tipos']}</p>"
        f"<p><img src='{dados['imagem']}' alt='{dados['nome']}' /></p>"
    )

    payload = {
        "ticket": {
            "comment": {
                "html_body": html_body,
                "public": True
            },
            "tags": ["-teste_pokeapi"]  # remove a tag após o update
        }
    }

    url = f"https://{ZENDESK_SUBDOMINIO}.zendesk.com/api/v2/tickets/{ticket_id}.json"
    res = requests.put(url, headers=get_auth_header(), json=payload)
    return res.status_code == 200 or res.status_code == 201

# === WEBHOOK ENDPOINT ===
@app.route('/webhook-pokeapi', methods=['POST'])
def receber_webhook():
    data = request.json

    ticket_id = data.get('ticket_event', {}).get('ticket', {}).get('id')
    campos_customizados = data.get('ticket_event', {}).get('ticket', {}).get('custom_fields', [])

    pokemon = None
    for campo in campos_customizados:
        if campo.get('id') == int(CAMPO_CUSTOM_POKEMON.replace('custom_fields_', '')):
            pokemon = campo.get('value')
            break

    if not ticket_id or not pokemon:
        return jsonify({"error": "ID do ticket ou pokémon não encontrado"}), 400

    sucesso = atualizar_ticket(ticket_id, pokemon)
    return jsonify({"status": "sucesso" if sucesso else "erro ao atualizar o ticket"})

# === TESTE LOCAL PARA CRIAR UM TICKET ===
def criar_ticket_exemplo(pokemon):
    payload = {
        "ticket": {
            "subject": f"Pokémon: {pokemon}",
            "comment": {
                "body": f"Solicitação de dados sobre o pokémon {pokemon}"
            },
            "tags": ["teste_pokeapi"],
            "priority": "normal",
            "custom_fields": [
                {
                    "id": int(CAMPO_CUSTOM_POKEMON.replace('custom_fields_', '')),
                    "value": pokemon
                }
            ]
        }
    }

    url = f"https://{ZENDESK_SUBDOMINIO}.zendesk.com/api/v2/tickets.json"
    res = requests.post(url, headers=get_auth_header(), json=payload)

    if res.status_code == 201:
        ticket = res.json()['ticket']
        print(f"✅ Ticket criado com ID #{ticket['id']}")
    else:
        print(f"❌ Falha ao criar ticket: {res.status_code}")
        print(res.text)

if __name__ == '__main__':
    # Apenas para teste local — pode comentar se estiver rodando em produção
    # criar_ticket_exemplo("bulbasaur")
    app.run(port=3000)