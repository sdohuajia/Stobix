from aiohttp import (
    ClientResponseError,
    ClientSession,
    ClientTimeout
)
from aiohttp_socks import ProxyConnector
from fake_useragent import FakeUserAgent
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import to_hex
from datetime import datetime, timezone
from colorama import *
import asyncio, os, json, pytz

wib = pytz.timezone('Asia/Jakarta')

class Stobix:
    def __init__(self) -> None:
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://app.stobix.com",
            "Referer": "https://app.stobix.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": FakeUserAgent().random
        }
        self.BASE_API = "https://api.stobix.com/v1"
        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}
        self.nonce = {}
        self.message = {}
        self.tokens = {}

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def log(self, message):
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}{message}",
            flush=True
        )

    def welcome(self):
        print(
            f"""
        {Fore.GREEN + Style.BRIGHT}自动领取 {Fore.BLUE + Style.BRIGHT}Stobix - 机器人
            """
            f"""
        {Fore.GREEN + Style.BRIGHT}Rey? {Fore.YELLOW + Style.BRIGHT}<这是水印>
            """
        )

    def format_seconds(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    
    async def load_proxies(self, use_proxy_choice: int):
        filename = "proxy.txt"
        try:
            if use_proxy_choice == 1:
                async with ClientSession(timeout=ClientTimeout(total=30)) as session:
                    async with session.get("https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text") as response:
                        response.raise_for_status()
                        content = await response.text()
                        with open(filename, 'w') as f:
                            f.write(content)
                        self.proxies = [line.strip() for line in content.splitlines() if line.strip()]
            else:
                if not os.path.exists(filename):
                    self.log(f"{Fore.RED + Style.BRIGHT}文件 {filename} 未找到。{Style.RESET_ALL}")
                    return
                with open(filename, 'r') as f:
                    self.proxies = [line.strip() for line in f.read().splitlines() if line.strip()]
            
            if not self.proxies:
                self.log(f"{Fore.RED + Style.BRIGHT}未找到代理。{Style.RESET_ALL}")
                return

            self.log(
                f"{Fore.GREEN + Style.BRIGHT}代理总数  : {Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT}{len(self.proxies)}{Style.RESET_ALL}"
            )
        
        except Exception as e:
            self.log(f"{Fore.RED + Style.BRIGHT}加载代理失败: {e}{Style.RESET_ALL}")
            self.proxies = []

    def check_proxy_schemes(self, proxies):
        schemes = ["http://", "https://", "socks4://", "socks5://"]
        if any(proxies.startswith(scheme) for scheme in schemes):
            return proxies
        return f"http://{proxies}"

    def get_next_proxy_for_account(self, account):
        if account not in self.account_proxies:
            if not self.proxies:
                return None
            proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
            self.account_proxies[account] = proxy
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return self.account_proxies[account]

    def rotate_proxy_for_account(self, account):
        if not self.proxies:
            return None
        proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
        self.account_proxies[account] = proxy
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return proxy
        
    def generate_address(self, account: str):
        try:
            account = Account.from_key(account)
            address = account.address
            return address
        except Exception as e:
            return None
    
    def generate_payload(self, account: str, address: str):
        try:
            encoded_message = encode_defunct(text=self.message[address])
            signed_message = Account.sign_message(encoded_message, private_key=account)
            signature = to_hex(signed_message.signature)

            payload = {
                "nonce":self.nonce[address],
                "signature":signature
            }

            return payload
        except Exception as e:
            raise Exception(f"生成请求负载失败: {str(e)}")
    
    def mask_account(self, account):
        try:
            mask_account = account[:6] + '*' * 6 + account[-6:]
            return mask_account
        except Exception as e:
            return None

    def print_question(self):
        while True:
            try:
                print(f"{Fore.WHITE + Style.BRIGHT}1. 使用免费 Proxyscrape 代理运行{Style.RESET_ALL}")
                print(f"{Fore.WHITE + Style.BRIGHT}2. 使用私有代理运行{Style.RESET_ALL}")
                print(f"{Fore.WHITE + Style.BRIGHT}3. 无代理运行{Style.RESET_ALL}")
                choose = int(input(f"{Fore.BLUE + Style.BRIGHT}选择 [1/2/3] -> {Style.RESET_ALL}").strip())

                if choose in [1, 2, 3]:
                    proxy_type = (
                        "使用免费 Proxyscrape" if choose == 1 else 
                        "使用私有" if choose == 2 else 
                        "无"
                    )
                    print(f"{Fore.GREEN + Style.BRIGHT}已选择运行{proxy_type}代理。{Style.RESET_ALL}")
                    break
                else:
                    print(f"{Fore.RED + Style.BRIGHT}请输入 1、2 或 3。{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED + Style.BRIGHT}输入无效，请输入数字（1、2 或 3）。{Style.RESET_ALL}")

        rotate = False
        if choose in [1, 2]:
            while True:
                rotate = input(f"{Fore.BLUE + Style.BRIGHT}是否旋转无效代理？[y/n] -> {Style.RESET_ALL}").strip()

                if rotate in ["y", "n"]:
                    rotate = rotate == "y"
                    break
                else:
                    print(f"{Fore.RED + Style.BRIGHT}输入无效，请输入 'y' 或 'n'。{Style.RESET_ALL}")

        return choose, rotate
    
    async def auth_nonce(self, address: str, proxy=None, retries=5):
        url = f"{self.BASE_API}/auth/nonce"
        data = json.dumps({"address":address})
        headers = {
            **self.headers,
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy) if proxy else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, data=data, ssl=False) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.CYAN + Style.BRIGHT}状态    :{Style.RESET_ALL}"
                    f"{Fore.RED + Style.BRIGHT} 获取 Nonce 失败 {Style.RESET_ALL}"
                    f"{Fore.MAGENTA + Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.RED + Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )
        
        return None
    
    async def auth_verify(self, account: str, address: str, proxy=None, retries=5):
        url = f"{self.BASE_API}/auth/web3/verify"
        data = json.dumps(self.generate_payload(account, address))
        headers = {
            **self.headers,
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy) if proxy else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, data=data, ssl=False) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.CYAN + Style.BRIGHT}状态    :{Style.RESET_ALL}"
                    f"{Fore.RED + Style.BRIGHT} 登录失败 {Style.RESET_ALL}"
                    f"{Fore.MAGENTA + Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.RED + Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )
        
        return None
    
    async def user_loyality(self, address: str, proxy=None, retries=5):
        url = f"{self.BASE_API}/loyalty"
        headers = {
            **self.headers,
            "Authorization": f"Bearer {self.tokens[address]}"
        }
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy) if proxy else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.get(url=url, headers=headers, ssl=False) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.CYAN + Style.BRIGHT}错误     :{Style.RESET_ALL}"
                    f"{Fore.RED + Style.BRIGHT} 获取用户数据失败 {Style.RESET_ALL}"
                    f"{Fore.MAGENTA + Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.RED + Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )
        
        return None
    
    async def perform_mining(self, address: str, proxy=None, retries=5):
        url = f"{self.BASE_API}/loyalty/points/mine"
        headers = {
            **self.headers,
            "Authorization": f"Bearer {self.tokens[address]}",
            "Content-Length": "0"
        }
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy) if proxy else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, ssl=False) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.MAGENTA + Style.BRIGHT}   > {Style.RESET_ALL}"
                    f"{Fore.RED + Style.BRIGHT} 未开始 {Style.RESET_ALL}"
                    f"{Fore.MAGENTA + Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.RED + Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )
        
        return None
    
    async def claim_mining(self, address: str, proxy=None, retries=5):
        url = f"{self.BASE_API}/loyalty/points/claim"
        headers = {
            **self.headers,
            "Authorization": f"Bearer {self.tokens[address]}",
            "Content-Length": "0"
        }
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy) if proxy else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, ssl=False) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.MAGENTA + Style.BRIGHT}   > {Style.RESET_ALL}"
                    f"{Fore.RED + Style.BRIGHT} 未领取 {Style.RESET_ALL}"
                    f"{Fore.MAGENTA + Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.RED + Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )
        
        return None
    
    async def claim_tasks(self, address: str, task_id: str, proxy=None, retries=5):
        url = f"{self.BASE_API}/loyalty/tasks/claim"
        data = json.dumps({"taskId":task_id})
        headers = {
            **self.headers,
            "Authorization": f"Bearer {self.tokens[address]}",
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy) if proxy else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, data=data, ssl=False) as response:
                        if response.status == 400:
                            self.log(
                                f"{Fore.MAGENTA + Style.BRIGHT}   > {Style.RESET_ALL}"
                                f"{Fore.WHITE + Style.BRIGHT}{task_id}{Style.RESET_ALL}"
                                f"{Fore.RED + Style.BRIGHT} 未领取 {Style.RESET_ALL}"
                                f"{Fore.MAGENTA + Style.BRIGHT}或{Style.RESET_ALL}"
                                f"{Fore.YELLOW + Style.BRIGHT} 已领取 {Style.RESET_ALL}"
                            )
                            return None
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.MAGENTA + Style.BRIGHT}   > {Style.RESET_ALL}"
                    f"{Fore.WHITE + Style.BRIGHT}{task_id}{Style.RESET_ALL}"
                    f"{Fore.RED + Style.BRIGHT} 未领取 {Style.RESET_ALL}"
                    f"{Fore.MAGENTA + Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.RED + Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )
        
        return None

    async def process_auth_nonce(self, address: str, use_proxy: bool, rotate_proxy: bool):
        while True:
            proxy = self.get_next_proxy_for_account(address) if use_proxy else None
            self.log(
                f"{Fore.CYAN + Style.BRIGHT}代理     :{Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT} {proxy} {Style.RESET_ALL}"
            )

            nonce = await self.auth_nonce(address, proxy)
            if nonce:
                self.nonce[address] = nonce["nonce"]
                self.message[address] = nonce["message"]
                return True
            
            if rotate_proxy:
                proxy = self.rotate_proxy_for_account(address)
                await asyncio.sleep(5)
                continue

            return False
        
    async def process_auth_verify(self, account: str, address: str, use_proxy: bool, rotate_proxy: bool):
        nonce = await self.process_auth_nonce(address, use_proxy, rotate_proxy)
        if nonce:
            proxy = self.get_next_proxy_for_account(address) if use_proxy else None
            
            verify = await self.auth_verify(account, address, proxy)
            if verify:
                self.tokens[address] = verify["token"]
                self.log(
                    f"{Fore.CYAN + Style.BRIGHT}状态    :{Style.RESET_ALL}"
                    f"{Fore.GREEN + Style.BRIGHT} 登录成功 {Style.RESET_ALL}"
                )
                return True
            return False
        
    async def process_accounts(self, account: str, address: str, use_proxy: bool, rotate_proxy: bool):
        verifed = await self.process_auth_verify(account, address, use_proxy, rotate_proxy)
        if verifed:
            proxy = self.get_next_proxy_for_account(address) if use_proxy else None
            
            user = await self.user_loyality(address, proxy)
            if not user:
                return
            
            points = user.get("user", {}).get("points", 0)
            self.log(
                f"{Fore.CYAN + Style.BRIGHT}余额   :{Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT} {points} $SBXP {Style.RESET_ALL}"
            )

            self.log(f"{Fore.CYAN + Style.BRIGHT}挖矿    :{Style.RESET_ALL}")

            mining_start_at = user.get("user", {}).get("miningStartedAt", None)

            if mining_start_at is None:
                start = await self.perform_mining(address, proxy)
                if start:
                    self.log(
                        f"{Fore.MAGENTA + Style.BRIGHT}   > {Style.RESET_ALL}"
                        f"{Fore.GREEN + Style.BRIGHT} 启动成功 {Style.RESET_ALL}"
                    )
            else:
                utc_now = datetime.now(timezone.utc)
                mining_claim_utc = datetime.fromisoformat(user["user"]["miningClaimAt"].replace("Z", "+00:00"))
                mining_claim_wib = mining_claim_utc.astimezone(wib).strftime('%x %X %Z')

                if utc_now >= mining_claim_utc:
                    mining_reward = user.get("user", {}).get("miningAmount", None)

                    claim = await self.claim_mining(address, proxy)
                    if claim:
                        self.log(
                            f"{Fore.MAGENTA + Style.BRIGHT}   > {Style.RESET_ALL}"
                            f"{Fore.GREEN + Style.BRIGHT} 领取成功 {Style.RESET_ALL}"
                            f"{Fore.MAGENTA + Style.BRIGHT}-{Style.RESET_ALL}"
                            f"{Fore.CYAN + Style.BRIGHT} 奖励: {Style.RESET_ALL}"
                            f"{Fore.WHITE + Style.BRIGHT}{mining_reward} $SBXP{Style.RESET_ALL}"
                        )

                        start = await self.perform_mining(address, proxy)
                        if start:
                            self.log(
                                f"{Fore.MAGENTA + Style.BRIGHT}   > {Style.RESET_ALL}"
                                f"{Fore.GREEN + Style.BRIGHT} 启动成功 {Style.RESET_ALL}"
                            )
                    
                else:
                    self.log(
                        f"{Fore.MAGENTA + Style.BRIGHT}   > {Style.RESET_ALL}"
                        f"{Fore.YELLOW + Style.BRIGHT} 已启动 {Style.RESET_ALL}"
                        f"{Fore.MAGENTA + Style.BRIGHT}-{Style.RESET_ALL}"
                        f"{Fore.CYAN + Style.BRIGHT} 领取时间: {Style.RESET_ALL}"
                        f"{Fore.WHITE + Style.BRIGHT}{mining_claim_wib}{Style.RESET_ALL}"
                    )

            tasks = user.get("tasks", [])
            if tasks:
                self.log(f"{Fore.CYAN + Style.BRIGHT}任务列表:{Style.RESET_ALL}")

                for task in tasks:
                    if task:
                        task_id = task.get("id")
                        reward = task.get("points")
                        frequency = task.get("frequency")
                        claimed_at = task.get("claimedAt")

                        if frequency == "once":
                            if claimed_at is not None:
                                self.log(
                                    f"{Fore.MAGENTA + Style.BRIGHT}   > {Style.RESET_ALL}"
                                    f"{Fore.WHITE + Style.BRIGHT}{task_id}{Style.RESET_ALL}"
                                    f"{Fore.YELLOW + Style.BRIGHT} 已完成 {Style.RESET_ALL}"
                                )
                                continue

                            if "create" in task_id or task_id == "publish_video":
                                self.log(
                                    f"{Fore.MAGENTA + Style.BRIGHT}   > {Style.RESET_ALL}"
                                    f"{Fore.WHITE + Style.BRIGHT}{task_id}{Style.RESET_ALL}"
                                    f"{Fore.YELLOW + Style.BRIGHT} 已跳过 {Style.RESET_ALL}"
                                )
                                continue

                            claim = await self.claim_tasks(address, task_id, proxy)
                            if claim:
                                self.log(
                                    f"{Fore.MAGENTA + Style.BRIGHT}   > {Style.RESET_ALL}"
                                    f"{Fore.WHITE + Style.BRIGHT}{task_id}{Style.RESET_ALL}"
                                    f"{Fore.GREEN + Style.BRIGHT} 领取成功 {Style.RESET_ALL}"
                                    f"{Fore.MAGENTA + Style.BRIGHT}-{Style.RESET_ALL}"
                                    f"{Fore.CYAN + Style.BRIGHT} 奖励: {Style.RESET_ALL}"
                                    f"{Fore.WHITE + Style.BRIGHT}{reward} $SBXP{Style.RESET_ALL}"
                                )

                        elif frequency == "daily":
                            claim = await self.claim_tasks(address, task_id, proxy)
                            if claim:
                                self.log(
                                    f"{Fore.MAGENTA + Style.BRIGHT}   > {Style.RESET_ALL}"
                                    f"{Fore.WHITE + Style.BRIGHT}{task_id}{Style.RESET_ALL}"
                                    f"{Fore.GREEN + Style.BRIGHT} 领取成功 {Style.RESET_ALL}"
                                    f"{Fore.MAGENTA + Style.BRIGHT}-{Style.RESET_ALL}"
                                    f"{Fore.CYAN + Style.BRIGHT} 奖励: {Style.RESET_ALL}"
                                    f"{Fore.WHITE + Style.BRIGHT}{reward} $SBXP{Style.RESET_ALL}"
                                )
            else:
                self.log(
                    f"{Fore.CYAN + Style.BRIGHT}任务列表:{Style.RESET_ALL}"
                    f"{Fore.YELLOW + Style.BRIGHT} 无可用任务 {Style.RESET_ALL}"
                )

    async def main(self):
        try:
            with open('accounts.txt', 'r') as file:
                accounts = [line.strip() for line in file if line.strip()]

            use_proxy_choice, rotate_proxy = self.print_question()

            use_proxy = False
            if use_proxy_choice in [1, 2]:
                use_proxy = True

            while True:
                self.clear_terminal()
                self.welcome()
                self.log(
                    f"{Fore.GREEN + Style.BRIGHT}账户总数: {Style.RESET_ALL}"
                    f"{Fore.WHITE + Style.BRIGHT}{len(accounts)}{Style.RESET_ALL}"
                )

                if use_proxy:
                    await self.load_proxies(use_proxy_choice)

                separator = "=" * 25
                for account in accounts:
                    if account:
                        address = self.generate_address(account)
                        self.log(
                            f"{Fore.CYAN + Style.BRIGHT}{separator}[{Style.RESET_ALL}"
                            f"{Fore.WHITE + Style.BRIGHT} {self.mask_account(address)} {Style.RESET_ALL}"
                            f"{Fore.CYAN + Style.BRIGHT}]{separator}{Style.RESET_ALL}"
                        )

                        if not address:
                            self.log(
                                f"{Fore.CYAN + Style.BRIGHT}状态    :{Style.RESET_ALL}"
                                f"{Fore.RED + Style.BRIGHT} 无效私钥或库版本不支持 {Style.RESET_ALL}"
                            )
                            continue
                        
                        await self.process_accounts(account, address, use_proxy, rotate_proxy)
                        await asyncio.sleep(3)

                self.log(f"{Fore.CYAN + Style.BRIGHT}={Style.RESET_ALL}"*72)
                
                delay = 8 * 60 * 60
                while delay > 0:
                    formatted_time = self.format_seconds(delay)
                    print(
                        f"{Fore.CYAN+Style.BRIGHT}[ 等待{Style.RESET_ALL}"
                        f"{Fore.WHITE+Style.BRIGHT} {formatted_time} {Style.RESET_ALL}"
                        f"{Fore.CYAN+Style.BRIGHT}... ]{Style.RESET_ALL}"
                        f"{Fore.WHITE+Style.BRIGHT} | {Style.RESET_ALL}"
                        f"{Fore.BLUE+Style.BRIGHT}所有账户已处理完成...{Style.RESET_ALL}",
                        end="\r",
                        flush=True
                    )
                    await asyncio.sleep(1)
                    delay -= 1

        except FileNotFoundError:
            self.log(f"{Fore.RED}文件 'accounts.txt' 未找到。{Style.RESET_ALL}")
            return
        except Exception as e:
            self.log(f"{Fore.RED+Style.BRIGHT}错误: {e}{Style.RESET_ALL}")
            raise

if __name__ == "__main__":
    try:
        bot = Stobix()
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
            f"{Fore.RED + Style.BRIGHT}[ 退出 ] Stobix - 机器人{Style.RESET_ALL}"                              
        )