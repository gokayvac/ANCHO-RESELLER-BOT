import json, discord, os
from discord.ext import bridge, commands
from datetime import datetime, timedelta
from BotModules.JsonManager import JsonManager

class Fiyatlar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        JsonManager.ensure_json_files()
        self.bot_config = JsonManager.load_json('JSON/Bot.json', {"prefix": "!", "token": "", "admin_ids": []})
        self.reseller_data = JsonManager.load_json('JSON/Data.json', {"resellers": []})
        self.products = JsonManager.load_json('JSON/Products.json', {"products": []})

    def is_reseller(self, user_id):
        return JsonManager.is_reseller(user_id)

    def has_panel_access(self, user_id):
        try:
            with open('JSON/Data.json', 'r') as f:
                data = json.load(f)
                reseller = next((r for r in data['resellers'] if str(user_id) == r['discord_id']), None)
                return reseller and reseller.get('reseller_access', False)
        except (FileNotFoundError, json.JSONDecodeError):
            return False

    @bridge.bridge_command()
    async def fiyatlar(self, ctx):
        if not self.is_reseller(ctx.author.id): 
            return await ctx.respond("Bu komutu sadece reseller'lar kullanabilir! ⛔", ephemeral=True)
        
        if not self.has_panel_access(ctx.author.id):
            return await ctx.respond("Panel erişiminiz bulunmuyor veya dondurulmuş durumda! ⛔", ephemeral=True)
            
        if not self.products['products']: 
            return await ctx.respond("Henüz hiç ürün eklenmemiş.", ephemeral=True)

        embed = discord.Embed(title="Ancho Reseller Panel", description="Aşağıda mevcut ürünlerin listesi bulunmaktadır.", color=discord.Color.from_rgb(88, 101, 242))
        
        for product in self.products['products']:
            stock_status = "🟢 Stokta" if product['stock'] > 0 else "🔴 Tükendi"
            duration = "♾️ Sınırsız" if product['duration_days'] == -1 else f"⏳ {product['duration_days']} Gün"
            features_text = "• " + " • ".join(product['features']) if 'features' in product and product['features'] else "• Belirtilmemiş"
            
            embed.add_field(
                name=f"┃ {product['name']} (ID: {product['id']}) ┃",
                value=f"```⚡ Fiyat: ${product['price']:.2f}\n📅 Süre: {duration}\n📦 Stok: {stock_status}\n✨ Özellikler:\n{features_text}```",
                inline=False
            )

        embed.set_footer(text="Satın almak için aşağıdaki butonları kullanabilirsiniz.")
        embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/thumb/9/94/Riot_Vanguard_Logo_Sep_2024.svg/1200px-Riot_Vanguard_Logo_Sep_2024.svg.png")
        
        class ProductsView(discord.ui.View):
            def __init__(self, cog):
                super().__init__()
                for product in cog.products['products']:
                    button = ProductButton(product, cog)
                    if product['stock'] <= 0: button.disabled = True; button.style = discord.ButtonStyle.gray
                    self.add_item(button)

        class ProductButton(discord.ui.Button):
            def __init__(self, product, cog):
                super().__init__(label=f"🛒 {product['name']}", style=discord.ButtonStyle.green, custom_id=f"buy_{product['id']}")
                self.product, self.cog = product, cog

            async def callback(self, interaction):
                # Panel erişimini kontrol et
                if not self.cog.has_panel_access(interaction.user.id):
                    return await interaction.response.send_message("Panel erişiminiz bulunmuyor veya dondurulmuş durumda! ⛔", ephemeral=True)
                
                modal = discord.ui.Modal(title=f"🛍️ {self.product['name']} Satın Al")
                modal.add_item(discord.ui.InputText(label="📦 Miktar", placeholder="Örn: 1", value="1", min_length=1, max_length=2))
                
                async def modal_callback(interaction):
                    # Panel erişimini tekrar kontrol et
                    if not self.cog.has_panel_access(interaction.user.id):
                        return await interaction.response.send_message("Panel erişiminiz bulunmuyor veya dondurulmuş durumda! ⛔", ephemeral=True)
                    
                    quantity = int(modal.children[0].value)
                    data = json.load(open('JSON/Data.json', 'r'))
                    reseller = next((r for r in data['resellers'] if str(interaction.user.id) == r['discord_id']), None)
                    
                    if not reseller: return await interaction.response.send_message("Reseller bilgileriniz bulunamadı.", ephemeral=True)
                    
                    total_cost = self.product['price'] * quantity
                    if reseller['balance'] < total_cost: return await interaction.response.send_message(f"Yetersiz bakiye! Gereken: ${total_cost:.2f}, Mevcut: ${reseller['balance']:.2f}", ephemeral=True)
                    if self.product['stock'] < quantity: return await interaction.response.send_message(f"Yetersiz stok! Mevcut stok: {self.product['stock']}", ephemeral=True)
                    
                    reseller['balance'] -= total_cost
                    self.product['stock'] -= quantity
                    if 'sales' not in reseller: reseller['sales'] = []
                    
                    licenses = []
                    for _ in range(quantity):
                        license_key = f"LIC-{interaction.user.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{_}"
                        expiry_date = (datetime.now() + timedelta(days=self.product['duration_days'])).strftime("%Y-%m-%d %H:%M:%S") if self.product['duration_days'] != -1 else "Sınırsız"
                        
                        reseller['sales'].append({
                            "product_id": self.product['id'], "license_key": license_key,
                            "purchase_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "expiry_date": expiry_date, "customer_id": str(interaction.user.id),
                            "customer_name": interaction.user.name, "status": "active", "hwid": ""
                        })
                        licenses.append(license_key)
                    
                    if 'balance_history' not in reseller: reseller['balance_history'] = []
                    reseller['balance_history'].append({
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "amount": -total_cost, "type": "purchase",
                        "description": f"{quantity}x {self.product['name']} satın alındı"
                    })
                    
                    JsonManager.save_json('JSON/Data.json', data)
                    JsonManager.save_json('JSON/Products.json', self.cog.products)
                    
                    embed = discord.Embed(title="✅ Satın Alma İşlemi Başarılı", description="Satın alma işleminiz başarıyla tamamlandı!", color=discord.Color.green())
                    embed.add_field(name="🛍️ Ürün Detayları", value=f"```• Ürün: {self.product['name']}\n• Miktar: {quantity}x\n• Toplam: ${total_cost:.2f}\n• Kalan Bakiye: ${reseller['balance']:.2f}```", inline=False)
                    embed.add_field(name="🔑 Lisans Anahtarları", value=f"```{chr(10).join(licenses)}```", inline=False)
                    embed.set_footer(text="💫 İyi kullanımlar dileriz!")
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                
                modal.callback = modal_callback
                await interaction.response.send_modal(modal)
        
        await ctx.respond(embed=embed, view=ProductsView(self), ephemeral=True)

def setup(bot): bot.add_cog(Fiyatlar(bot))