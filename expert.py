import socket
import sys
import locale
import builtins

# Safe print wrapper to prevent UnicodeEncodeError on Windows terminals
def safe_print(*args, **kwargs):
    encoding = sys.stdout.encoding or 'utf-8'
    new_args = []
    for arg in args:
        if isinstance(arg, str):
            new_args.append(arg.encode(encoding, errors='replace').decode(encoding))
        else:
            new_args.append(arg)
    builtins.print(*new_args, **kwargs)

# Override the default print function globally
print = safe_print

# Translation dictionary for expert panel internationalization (i18n)
LANG_STRINGS = {
    'tr': {
        'welcome_border': '==================================================',
        'welcome_title': '👨‍🌾 Botanik Uzmanı (Operatör) Paneline Hoş Geldiniz',
        'waiting_cases': 'Sistemden gelecek olan vakalar bekleniyor... (SOCKET İLE)',
        'exit_instruction': 'Çıkmak için CTRL+C yapabilirsiniz.',
        'socket_error': 'Socket başlatılamadı: {error}',
        'new_case': '[YENİ VAKA GELDİ]: Bota bir soru geldi, ne cevap verelim?',
        'user_question': 'Kullanıcının sorusu: {question}',
        'your_answer': 'Cevabınız: ',
        'answer_sent': 'Cevap sisteme iletildi. Yeni sorular bekleniyor...',
        'graceful_exit': '\nÇıkış yapılıyor...',
        'usage_error': 'Kullanım: python expert.py [--lang tr|en]'
    },
    'en': {
        'welcome_border': '==================================================',
        'welcome_title': '👨‍🌾 Welcome to the Botanist Expert (Operator) Panel',
        'waiting_cases': 'Waiting for incoming cases from the system... (VIA SOCKET)',
        'exit_instruction': 'You can press CTRL+C to exit.',
        'socket_error': 'Socket could not be initialized: {error}',
        'new_case': '[NEW CASE RECEIVED]: A question was sent to the bot, what should we answer?',
        'user_question': "User's question: {question}",
        'your_answer': 'Your answer: ',
        'answer_sent': 'Answer forwarded to the system. Waiting for new questions...',
        'graceful_exit': '\nExiting...',
        'usage_error': 'Usage: python expert.py [--lang tr|en]'
    }
}

# Auto-detect OS default language
def get_default_language():
    try:
        sys_lang = locale.getlocale()[0]
        if sys_lang:
            sys_lang_lower = sys_lang.lower()
            if sys_lang_lower.startswith('tr') or 'turkish' in sys_lang_lower:
                return 'tr'
    except:
        pass
    return 'en'

# Parse arguments for optional language
def parse_arguments():
    lang = get_default_language()
    if '--lang' in sys.argv:
        try:
            lang_idx = sys.argv.index('--lang')
            if lang_idx + 1 < len(sys.argv):
                provided_lang = sys.argv[lang_idx + 1].lower()
                if provided_lang in ['tr', 'en']:
                    lang = provided_lang
                sys.argv.pop(lang_idx + 1)
                sys.argv.pop(lang_idx)
        except ValueError:
            pass
            
    # Check if there are other unexpected arguments
    if len(sys.argv) > 1:
        print(LANG_STRINGS[lang]['usage_error'])
        sys.exit(1)
        
    return lang

def main():
    lang = parse_arguments()
    strings = LANG_STRINGS[lang]
    
    # Welcome banner for the botanist expert operator panel
    print(strings['welcome_border'])
    print(strings['welcome_title'])
    print(strings['waiting_cases'])
    print(strings['exit_instruction'])
    print(strings['welcome_border'])
    
    # Configure local host address and port for the socket server
    HOST = 'localhost'
    PORT = 5000
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Set socket option to reuse address to avoid "Address already in use" errors
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((HOST, PORT))
        # Listen for connections (limit backlog to 1 connection)
        server_socket.listen(1) 
    except Exception as error:
        print(strings['socket_error'].format(error=error))
        sys.exit(1)
        
    try:
        # Main server loop: Wait and process cases forwarded from the bot
        while True:
            # Block until a client connects
            client_socket, address = server_socket.accept()
            
            # Receive the question sent by the client
            question_data = client_socket.recv(1024)
            if not question_data:
                client_socket.close()
                continue
                
            question = question_data.decode('utf-8')
            
            # Display case details and prompt the expert to type an answer
            print(f"\n{strings['new_case']}")
            print(strings['user_question'].format(question=question))
            
            answer = input(strings['your_answer'])
            
            # Send the answer back to the client (bot.py)
            client_socket.sendall(answer.encode('utf-8'))
            print(strings['answer_sent'])
            
            # Close connection for the current query
            client_socket.close()
            
    except KeyboardInterrupt:
        # Graceful exit on keyboard interrupt (CTRL+C)
        print(strings['graceful_exit'])
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()
