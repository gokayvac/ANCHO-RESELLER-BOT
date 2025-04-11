import sys, os, discord, json, subprocess, time, platform, ctypes, shutil, itertools, threading, asyncio, aiohttp
from discord.ext import bridge, commands
from datetime import datetime, timedelta
from colorama import Fore, Style, init

init(autoreset=True)

class Bot(bridge.Bot):
    def __init__(self):
        start_time = time.time()
        with open('JSON/Bot.json', 'r') as f:
            self.config = json.load(f)
        super().__init__(command_prefix=self.config['configuration']['bot']['settings']['prefix'], intents=discord.Intents.all(), auto_sync_commands=True)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.start_time = datetime.now()
        self.animation_frame = 0
        self.load_modules()
        end_time = time.time()
        
    def load_modules(self):
        start_time = time.time()
        loaded_modules = 0
        for filename in os.listdir('./BotModules'):
            if filename.endswith('.py') and filename != 'JsonManager.py':
                module_start = time.time()
                self.load_extension(f'BotModules.{filename[:-3]}')
                loaded_modules += 1
                module_time = time.time() - module_start
                print(f"{Fore.LIGHTBLUE_EX}[{self.animate_loading()}] {Fore.WHITE}{filename} {Fore.LIGHTBLUE_EX}({module_time:.2f}s){Style.RESET_ALL}")
        end_time = time.time()
        print(f"{Fore.LIGHTBLUE_EX}[✓] {Fore.WHITE}Yüklenen modül: {Fore.GREEN}{loaded_modules} {Fore.LIGHTBLUE_EX}({end_time - start_time:.2f}s){Style.RESET_ALL}")
                
    async def on_ready(self):
        ready_start = time.time()
        terminal_width = shutil.get_terminal_size().columns
        print(f"\n{Fore.LIGHTBLUE_EX}{'-' * terminal_width}{Style.RESET_ALL}")
        bot_info = f"{self.user} ({self.user.id})"
        padding = (terminal_width - len(bot_info)) // 2
        print(f"{Fore.GREEN}{' ' * padding}{bot_info}{Style.RESET_ALL}")
        stats = f"Sunucu: {len(self.guilds)} | Kullanıcı: {len(set(self.get_all_members()))}"
        padding = (terminal_width - len(stats)) // 2
        print(f"{Fore.CYAN}{' ' * padding}{stats}{Style.RESET_ALL}")
        time_info = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        padding = (terminal_width - len(time_info)) // 2
        print(f"{Fore.YELLOW}{' ' * padding}{time_info}{Style.RESET_ALL}")
        print(f"{Fore.LIGHTBLUE_EX}{'-' * terminal_width}{Style.RESET_ALL}\n")
        if platform.system() == 'Windows': ctypes.windll.kernel32.SetConsoleTitleW(f"Ancho")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=self.config['configuration']['bot']['settings']['status']))
        sync_start = time.time()
        await self.sync_commands()
        sync_time = time.time() - sync_start
        print(f"{Fore.GREEN}[✓] {Fore.WHITE}Tüm komutlar senkronize edildi! {Fore.LIGHTBLUE_EX}({sync_time:.2f}s){Style.RESET_ALL}")
        ready_time = time.time() - ready_start
        print(f"{Fore.CYAN}Bot hazır! ({ready_time:.2f}s){Style.RESET_ALL}")
        self.loop.create_task(self.update_console_title())
        self.loop.create_task(self.reload_commands_periodically())
        
    def animate_loading(self):
        animations = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.animation_frame = (self.animation_frame + 1) % len(animations)
        return animations[self.animation_frame]
    
    def animate_progress(self, progress, total, width=30):
        filled_length = int(width * progress // total)
        bar = '█' * filled_length + '░' * (width - filled_length)
        percentage = progress / total * 100
        return f"[{bar}] {percentage:.1f}%"
    
    def animate_pulse(self):
        pulses = ["●", "○", "◎", "◉", "◎", "○"]
        return pulses[int(time.time() * 5) % len(pulses)]
    
    async def update_console_title(self):
        while True:
            if platform.system() == 'Windows':
                uptime = datetime.now() - self.start_time
                hours, remainder = divmod(uptime.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                uptime_str = f"{uptime.days}:{hours:02d}:{minutes:02d}:{seconds:02d}"
                ctypes.windll.kernel32.SetConsoleTitleW(f"Ancho | {uptime_str} | Sunucular: {len(self.guilds)}")
            await asyncio.sleep(1)
        
    async def close(self):
        close_start = time.time()
        await self.session.close()
        await super().close()
        close_time = time.time() - close_start
        print(f"{Fore.CYAN}Bot kapatıldı ({close_time:.2f}s){Style.RESET_ALL}")

    async def reload_all_extensions(self):
        reload_start = time.time()
        print(f"{Fore.CYAN}Tüm modüller yeniden yükleniyor...{Style.RESET_ALL}")
        total_modules = len([f for f in os.listdir('./BotModules') if f.endswith('.py') and f != 'JsonManager.py'])
        reloaded = 0
        for filename in os.listdir('./BotModules'):
            if filename.endswith('.py') and filename != 'JsonManager.py':
                try:
                    module_start = time.time()
                    self.reload_extension(f'BotModules.{filename[:-3]}')
                    reloaded += 1
                    module_time = time.time() - module_start
                    progress = self.animate_progress(reloaded, total_modules)
                    print(f"{Fore.LIGHTBLUE_EX}[✓] {Fore.WHITE}{filename} {Fore.LIGHTBLUE_EX}({module_time:.2f}s){Style.RESET_ALL}")
                except Exception as e:
                    if filename != 'JsonManager.py':
                        print(f"{Fore.LIGHTBLUE_EX}[✗] {Fore.WHITE}{filename} yeniden yüklenemedi: {e}{Style.RESET_ALL}")
        sync_start = time.time()
        await self.sync_commands()
        sync_time = time.time() - sync_start
        print(f"{Fore.GREEN}[✓] {Fore.WHITE}Tüm komutlar senkronize edildi! {Fore.LIGHTBLUE_EX}({sync_time:.2f}s){Style.RESET_ALL}")

    async def reload_commands_periodically(self):
        while True:
            await self.reload_all_extensions()
            await asyncio.sleep(1)

def run_spinner(stop_event, message):
    spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
    while not stop_event.is_set():
        sys.stdout.write(f"\r{Fore.LIGHTBLUE_EX}[{next(spinner)}] {Fore.WHITE}{message}{Style.RESET_ALL}")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write('\r')
    sys.stdout.flush()

if __name__ == '__main__':
    os.system('cls' if platform.system() == 'Windows' else 'clear')
    start_time = time.time()
    if platform.system() == 'Windows': ctypes.windll.kernel32.SetConsoleTitleW("Ancho | Başlatılıyor...")
    terminal_width = shutil.get_terminal_size().columns
    print(f"{Fore.LIGHTBLUE_EX}{'-' * terminal_width}{Style.RESET_ALL}")
    time_info = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    padding = (terminal_width - len(time_info)) // 2
    print(f"{Fore.YELLOW}{' ' * padding}{time_info}{Style.RESET_ALL}")
    print(f"{Fore.LIGHTBLUE_EX}{'-' * terminal_width}{Style.RESET_ALL}\n")
    bot_instance = Bot()
    bot_spinner_stop = threading.Event()
    bot_spinner_thread = threading.Thread(target=run_spinner, args=(bot_spinner_stop, "Discord botu başlatılıyor..."))
    bot_spinner_thread.start()
    time.sleep(1)
    bot_spinner_stop.set()
    bot_spinner_thread.join()
    print(f"{Fore.LIGHTBLUE_EX}[✓] {Fore.WHITE}Bot başlatıldı{Style.RESET_ALL}")
    try:
        bot_instance.run(bot_instance.config['configuration']['bot']['token'])
    except Exception as e:
        print(f"{Fore.RED}[✗] {Fore.WHITE}Bot başlatılamadı: {e}{Style.RESET_ALL}")
    finally:
        print(f"{Fore.CYAN}Toplam çalışma süresi: {time.time() - start_time:.2f}s{Style.RESET_ALL}")
