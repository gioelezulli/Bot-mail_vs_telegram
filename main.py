import imaplib
import email
from email.header import decode_header
import datetime
import logging
import tomllib
import os
import asyncio
from telegram import Bot

def load_config():

    # Definisce il percorso del file di configurazione
    config_path = os.path.join(os.path.dirname(__file__), 'Config', 'config.toml')

    # Legge il file config.toml usando tomllib
    with open(config_path, 'rb') as config_file:
        config = tomllib.load(config_file)

    return config

# Esempio di utilizzo della configurazione caricata
config = load_config()

# Inizio a loggare
logfile = os.path.join("Config", "Controllo.log")
logging.basicConfig(filename=logfile, level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s')

# Configurazione bot Telegram
TELEGRAM_BOT_TOKEN = config['telegram']['bot_token']
CHAT_ID = config['telegram']['authorized_users']

# Imposta l'applicazione
bot = Bot(token=TELEGRAM_BOT_TOKEN)
logging.info("bot avviato")
# Configurazione email
EMAIL = config['mail']['id_mail']
PASSWORD = config['mail']['psw_mail']
# Configurazione imap
IMAP_SERVER = config['imap']['imap_server']  # Adatta questo valore per il tuo provider di posta
IMAP_PORT = config['imap']['imap_port']
NUOVE_MAIL = config['imap']['ciclo_time']  # Controlla nuove email ogni X tempo
# Dominio da filtrare
DOMINIO = config['dominio']['filtra_dominio']

async def get_updates():
    try:
        updates = await bot.get_updates()
        for update in updates:
            print(f"Update trovato: {update}")
    except:
        logging.error("non riesco a connettermi a telegram")

# Esegui questa funzione per vedere gli aggiornamenti ricevuti dal bot
asyncio.run(get_updates())

def pulisci_mail(body):
    """
    Rimuove le righe che iniziano con '>>' dal corpo della mail.
    """
    # Suddividiamo il corpo della mail in righe
    righe = body.splitlines()

    # Filtriamo le righe che non iniziano con '>>'
    righe_pulite = [riga for riga in righe if not riga.strip().startswith('>>')]

    # Riuniamo le righe filtrate in un unico testo
    body_pulito = "\n".join(righe_pulite)

    return body_pulito

async def invia_notifica_telegram(subject, sender, body):
    """Inoltra il messaggio su Telegram."""
    # Pulisci il corpo della mail rimuovendo le righe che iniziano con '>>'
    body_pulito = pulisci_mail(body)[:500]  # Primi 500 caratteri del body
    messaggio = f"Oggetto: {subject}\nDa: {sender}\n\n{body_pulito}..."
    print(f"Invio messaggio a Telegram con CHAT_ID: {CHAT_ID}")  # Debug
    logging.info(f"Invio messaggio a Telegram con CHAT_ID: {CHAT_ID}")  # Debug
    print(f"Contenuto del messaggio: {messaggio}")  # Debug
    for chat_id in CHAT_ID:
        print(f"Invio messaggio alla chat con CHAT_ID: {chat_id}")  # Debug
    # Aggiungi tentativi di riprovo in caso di errore
        tentativi = 3
        for i in range(tentativi):
            try:
                await bot.send_message(chat_id=chat_id, text=messaggio)
                print(f"Notifica inviata a {chat_id}!")  # Debug
                logging.info(f"Notifica inviata a {chat_id}!")  # Debug
                break  # Se l'invio ha successo, esce dal ciclo di retry
            except Exception as e:
                print(f"Errore nell'invio del messaggio a {chat_id} (tentativo {i + 1}/{tentativi}): {e}")
                logging.error(f"Errore nell'invio del messaggio a {chat_id} (tentativo {i + 1}/{tentativi}): {e}")
                # Attende 2 secondi prima di ritentare
                await asyncio.sleep(2)
        else:
            # Se tutti i tentativi falliscono, restituisce False
            return False
    # Se tutte le notifiche sono state inviate correttamente, restituisce True
    return True

async def invia_notifica_giornaliera():
    """Invia una notifica giornaliera per confermare che il bot è in esecuzione."""
    messaggio = f"Controllo e-mail in funzione! Data e ora: {datetime.datetime.now()}"
    tutte_inviate = True  # Flag per tracciare se tutte le notifiche sono state inviate correttamente
    for chat_id in CHAT_ID:
        # Aggiungi tentativi di riprovo in caso di errore
        tentativi = 3
        for i in range(tentativi):
            try:
                await bot.send_message(chat_id=chat_id, text=messaggio)
                print(f"Notifica giornaliera inviata a {chat_id}")
                logging.info(f"Notifica giornaliera inviata a {chat_id}")
                break  # Se l'invio ha successo, esce dal ciclo di retry
            except Exception as e:
                print(f"Errore nell'invio della notifica giornaliera a {chat_id} (tentativo {i + 1}/{tentativi}): {e}")
                logging.error(f"Errore nell'invio della notifica giornaliera a {chat_id} (tentativo {i + 1}/{tentativi}): {e}")
                await asyncio.sleep(2)
        else:
            # Se tutti i tentativi falliscono per una chat, imposta il flag su False
            tutte_inviate = False

    # Se tutte le notifiche sono state inviate correttamente, restituisce True, altrimenti False
    return tutte_inviate


async def leggi_email():
    """Connettiti alla casella email e cerca le email provenienti dal dominio specificato."""
    print("Connessione al server IMAP...")  # Debug: inizio connessione
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(EMAIL, PASSWORD)
    print("Login effettuato!")  # Debug: login riuscito

    mail.select("inbox")  # Seleziona la casella di posta
    print("Casella inbox selezionata.")  # Debug: selezione casella

    # Data di inizio per l'ultimo mese
    ultimo_mese = (datetime.datetime.now() - datetime.timedelta(days=2)).strftime("%d-%b-%Y")   # Debug: ultimi 2 giorni

    # Cerca tutte le email non lette
    status, messaggi = mail.search(None, f'(UNSEEN SINCE {ultimo_mese})')
    print(f"Status della ricerca: {status}")  # Debug: stato della ricerca
    print(f"Email trovate: {messaggi[0].split()}")  # Debug: lista ID delle email trovate
    logging.info(f"Email trovate: {messaggi[0].split()}")  # Debug: lista ID delle email trovate

    # Estrai gli ID delle email non lette
    email_ids = messaggi[0].split()

    for email_id in email_ids:
        print(f"Lettura email con ID: {email_id}")  # Debug: ID dell'email corrente

        # Fetch della email per ID
        status, msg_data = mail.fetch(email_id, '(RFC822)')
        print(f"Status fetch: {status}")  # Debug: stato del fetch

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])

                # Decodifica l'oggetto dell'email
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    encoding = encoding if encoding and encoding.lower() != 'unknown-8bit' else 'utf-8'
                    subject = subject.decode(encoding)
                print(f"Oggetto email: {subject}")  # Debug: stampa oggetto email

                # Decodifica il mittente
                from_ = msg.get("From")
                print(f"Mittente email: {from_}")  # Debug: stampa mittente

                # Controlla se il mittente è del dominio specificato
                if any(dominio in from_ for dominio in DOMINIO):
                    print(f"Email proveniente dal dominio {DOMINIO} trovata!")  # Debug: dominio trovato

                    # Estrai il contenuto dell'email
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()

                    print(f"Corpo dell'email: {body[:50]}...")  # Debug: stampa parziale del corpo dell'email

                    # Tenta di inviare la notifica e reimposta l'email come non letta in caso di fallimento
                    successo = await invia_notifica_telegram(subject, from_, body)
                    if not successo:
                        await segna_non_letto(email_id, mail)
                        print(f"Notifica non inviata. Email da {from_} reimpostata come non letta.")
                        logging.info(f"Notifica non inviata. Email da {from_} reimpostata come non letta.")
                    await asyncio.sleep(2)  # Pausa tra invii per evitare sovraccarico
                else:
                    # Se il dominio non corrisponde, reimposta l'email come non letta
                    await segna_non_letto(email_id, mail)
                    print(f"Email da {from_} reimpostata come non letta (non dal dominio {DOMINIO}).")  # Debug: dominio non corrispondente

    # Logout dal server IMAP
    mail.logout()
    print("Logout dal server IMAP.")  # Debug: logout riuscito

async def segna_non_letto(email_id, mail):
    mail.store(email_id, '-FLAGS', '\\Seen')

# Ciclo infinito per controllare nuove email periodicamente
async def main():
    ultimo_controllo = datetime.datetime.now() - datetime.timedelta(days=1)  # Inizializza al giorno precedente
    while True:
        print("Controllo nuove email...")
        await leggi_email()

        # Verifica se è trascorso un giorno dall'ultimo controllo
        if (datetime.datetime.now() - ultimo_controllo).days >= 1:
            successo = await invia_notifica_giornaliera()
            await asyncio.sleep(2)  # Pausa tra invii per evitare sovraccarico
            if successo:
                # Se la notifica è stata inviata con successo a tutte le chat, aggiorna ultimo_controllo
                ultimo_controllo = datetime.datetime.now()
            else:
                print("Notifica giornaliera non inviata a tutte le chat, riproverò al prossimo ciclo.")
                logging.info(f"Notifica giornaliera non inviata a tutte le chat, riproverò al prossimo ciclo.")
        print("Attesa 60 secondi per nuovo controllo...")
        await asyncio.sleep(NUOVE_MAIL)

# Esegui il ciclo asincrono
asyncio.run(main())
