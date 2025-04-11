import discord, json, os, sys
from datetime import datetime, timedelta
from discord.ext import bridge, commands
from discord.ui import View, Select, Button
from BotModules.JsonManager import JsonManager
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
class Admin(commands.Cog):
    def __init__(self, bot): self.bot = bot; self.admin_role_id = int(json.load(open("JSON/Bot.json", "r", encoding="utf-8"))["configuration"]["server"]["roles"]["staff"]["admin"])
 
 
    @bridge.bridge_command(name="admin", description="Admin işlemlerini gerçekleştirir") 
    async def admin(self, ctx):
        if not any(role.id == self.admin_role_id for role in ctx.author.roles): return await ctx.respond("❌ Bu komutu kullanmak için yeterli yetkiye sahip değilsiniz.", ephemeral=True)
        embed = discord.Embed(title="🛡️ Admin Kontrol Paneli", description="Aşağıdaki menüden yapmak istediğiniz işlemi seçiniz.", color=discord.Color.from_rgb(88, 101, 242))
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/123456789/123456789/admin_icon.png")
        embed.add_field(name="📊 Bakiye İşlemleri", value="Kullanıcılara bakiye ekleyebilir veya çıkarabilirsiniz.", inline=False)
        embed.add_field(name="🔑 Panel Erişimi", value="Kullanıcılara panel erişimi verebilirsiniz.", inline=False)
        embed.add_field(name="🔒 Panel Erişimi Dondurma", value="Kullanıcıların panel erişimini dondurabilir veya açabilirsiniz.", inline=False)
        embed.add_field(name="📜 Reseller Bilgileri", value="Reseller bilgilerini görüntüleyebilirsiniz.", inline=False)
        embed.set_footer(text=f"İsteyen: {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
   
   
        class AdminView(discord.ui.View):
            def __init__(self, cog): super().__init__(timeout=300); self.cog = cog
            @discord.ui.select(placeholder="İşlem Seçiniz", options=[discord.SelectOption(label="Bakiye Ekle", description="Kullanıcıya bakiye ekler", emoji="💰", value="add_balance"), discord.SelectOption(label="Bakiye Çıkar", description="Kullanıcıdan bakiye alır", emoji="💸", value="remove_balance"), discord.SelectOption(label="Panel Erişimi Ver", description="Kullanıcıya panel erişimi verir", emoji="🔑", value="give_panel"), discord.SelectOption(label="Panel Erişimi Dondur", description="Kullanıcının panel erişimini dondurur", emoji="🔒", value="freeze_panel"), discord.SelectOption(label="Panel Erişimi Aç", description="Kullanıcının panel erişimini açar", emoji="🔓", value="unfreeze_panel"), discord.SelectOption(label="Tüm Panel Erişimlerini Dondur", description="Tüm kullanıcıların panel erişimini dondurur", emoji="❄️", value="freeze_all_panels"), discord.SelectOption(label="Tüm Panel Erişimlerini Aç", description="Tüm kullanıcıların panel erişimini açar", emoji="🌡️", value="unfreeze_all_panels"), discord.SelectOption(label="Reseller Bilgileri", description="Reseller bilgilerini görüntüler", emoji="📜", value="reseller_info")])
            async def select_operation(self, select, interaction):
                operation = select.values[0]
                if operation in ["add_balance", "remove_balance"]:
                    modal = discord.ui.Modal(title="Bakiye İşlemi" if operation == "add_balance" else "Bakiye Çıkarma")
                    user_id_input = discord.ui.InputText(label="Kullanıcı ID", placeholder="İşlem yapılacak kullanıcının ID'sini girin", required=True)
                    amount_input = discord.ui.InputText(label="Miktar", placeholder="Eklenecek/çıkarılacak bakiye miktarını girin", required=True)
                    modal.add_item(user_id_input); modal.add_item(amount_input)
                    async def modal_callback(interaction):
                        try:
                            user_id = int(user_id_input.value); amount = float(amount_input.value); user = await self.cog.bot.fetch_user(user_id)
                            if not user: return await interaction.response.send_message("❌ Kullanıcı bulunamadı.", ephemeral=True)
                            if operation == "add_balance": await self.process_add_balance(interaction, user, amount)
                            else: await self.process_remove_balance(interaction, user, amount)
                        except ValueError: await interaction.response.send_message("❌ Geçersiz ID veya miktar girdiniz.", ephemeral=True)
                        except Exception as e: await interaction.response.send_message(f"❌ Bir hata oluştu: {str(e)}", ephemeral=True)
                    modal.callback = modal_callback; await interaction.response.send_modal(modal)
                elif operation == "give_panel":
                    modal = discord.ui.Modal(title="Panel Erişimi Ver")
                    user_id_input = discord.ui.InputText(label="Kullanıcı ID", placeholder="Panel erişimi verilecek kullanıcının ID'sini girin", required=True)
                    days_input = discord.ui.InputText(label="Süre (Gün)", placeholder="Erişim süresini gün cinsinden girin", required=True)
                    modal.add_item(user_id_input); modal.add_item(days_input)
                    async def modal_callback(interaction):
                        try:
                            user_id = int(user_id_input.value); days = int(days_input.value); user = await self.cog.bot.fetch_user(user_id)
                            if not user: return await interaction.response.send_message("❌ Kullanıcı bulunamadı.", ephemeral=True)
                            await self.process_give_panel(interaction, user, days)
                        except ValueError: await interaction.response.send_message("❌ Geçersiz ID veya süre girdiniz.", ephemeral=True)
                        except Exception as e: await interaction.response.send_message(f"❌ Bir hata oluştu: {str(e)}", ephemeral=True)
                    modal.callback = modal_callback; await interaction.response.send_modal(modal)
                elif operation in ["freeze_panel", "unfreeze_panel"]:
                    modal = discord.ui.Modal(title="Panel Erişimi Dondur" if operation == "freeze_panel" else "Panel Erişimi Aç")
                    user_id_input = discord.ui.InputText(label="Kullanıcı ID", placeholder="İşlem yapılacak kullanıcının ID'sini girin", required=True)
                    modal.add_item(user_id_input)
                    async def modal_callback(interaction):
                        try:
                            user_id = int(user_id_input.value); user = await self.cog.bot.fetch_user(user_id)
                            if not user: return await interaction.response.send_message("❌ Kullanıcı bulunamadı.", ephemeral=True)
                            if operation == "freeze_panel": await self.process_freeze_panel(interaction, user)
                            else: await self.process_unfreeze_panel(interaction, user)
                        except ValueError: await interaction.response.send_message("❌ Geçersiz ID girdiniz.", ephemeral=True)
                        except Exception as e: await interaction.response.send_message(f"❌ Bir hata oluştu: {str(e)}", ephemeral=True)
                    modal.callback = modal_callback; await interaction.response.send_modal(modal)
                elif operation == "freeze_all_panels": await self.process_freeze_all_panels(interaction)
                elif operation == "unfreeze_all_panels": await self.process_unfreeze_all_panels(interaction)
                elif operation == "reseller_info": await self.show_reseller_info(interaction)
    
    
            async def show_reseller_info(self, interaction):
                reseller_data = JsonManager.load_json('JSON/Data.json', {"resellers": []}); resellers = reseller_data['resellers']
                if not resellers: return await interaction.response.send_message("Hiçbir reseller bulunamadı.", ephemeral=True)
                options = [discord.SelectOption(label=r['discord_name'], value=r['discord_id']) for r in resellers]; select = Select(placeholder="Bir reseller seçin", options=options)
                async def select_callback(interaction):
                    selected_reseller = next((r for r in resellers if r['discord_id'] == select.values[0]), None)
                    if not selected_reseller: return await interaction.response.send_message("Reseller bulunamadı.", ephemeral=True)
                    total_sales = sum(1 for sale in selected_reseller.get('sales', []) if sale.get('customer_id') and sale['customer_id'] != selected_reseller['discord_id'])
                    inventory_products = [sale['product_id'] for sale in selected_reseller.get('sales', []) if sale.get('customer_id') == selected_reseller['discord_id']]
                    embed = discord.Embed(title=f"📜 Reseller Bilgisi: {selected_reseller['discord_name']}", color=discord.Color.blue())
                    embed.add_field(name="🆔 Discord ID", value=selected_reseller['discord_id'], inline=False)
                    embed.add_field(name="🔑 Reseller Erişimi", value="✅" if selected_reseller.get('reseller_access', False) else "❌", inline=False)
                    embed.add_field(name="📅 Panel Bitiş Tarihi", value=selected_reseller.get('panel_expiry', 'Belirtilmemiş'), inline=False)
                    embed.add_field(name="💰 Bakiye", value=f"{selected_reseller.get('balance', 0)} TL", inline=False)
                    embed.add_field(name="🛒 Toplam Satış", value=f"{total_sales} satış", inline=False)
                    embed.add_field(name="📦 Envanterdeki Ürünler", value=", ".join(inventory_products) if inventory_products else "Yok", inline=False)
                    back_button = Button(label="Geri", style=discord.ButtonStyle.primary)
                    async def back_callback(interaction): await interaction.response.edit_message(content="Bir reseller seçin", embed=None, view=view_with_select)
                    back_button.callback = back_callback; view_with_back = View(); view_with_back.add_item(back_button)
                    await interaction.response.edit_message(content=None, embed=embed, view=view_with_back)
                select.callback = select_callback; view_with_select = View(); view_with_select.add_item(select)
                await interaction.response.send_message("Bir reseller seçin", view=view_with_select, ephemeral=True)
      
      
            async def process_add_balance(self, interaction, user, amount):
                try:
                    data = JsonManager.load_json("JSON/Data.json", {"resellers": []}); reseller = next((r for r in data["resellers"] if r["discord_id"] == str(user.id)), None)
                    if reseller: reseller["balance"] += amount
                    else: data["resellers"].append({"discord_name": user.name, "discord_id": str(user.id), "reseller_access": True, "balance": amount, "sales": []})
                    JsonManager.save_json("JSON/Data.json", data)
                    embed = discord.Embed(title="✅ Bakiye Ekleme Başarılı", description=f"{user.mention} kullanıcısına {amount} bakiye eklendi.", color=discord.Color.green())
                    embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
                    embed.add_field(name="İşlem Detayları", value=f"**Kullanıcı:** {user.name}\n**Eklenen Miktar:** {amount}\n**Tarih:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except Exception as e: await interaction.response.send_message(f"❌ Bir hata oluştu: {str(e)}", ephemeral=True)
      
      
            async def process_remove_balance(self, interaction, user, amount):
                try:
                    data = JsonManager.load_json("JSON/Data.json", {"resellers": []}); reseller = next((r for r in data["resellers"] if r["discord_id"] == str(user.id)), None)
                    if not reseller: return await interaction.response.send_message(f"❌ {user.mention} kullanıcısı reseller listesinde bulunamadı.", ephemeral=True)
                    if reseller["balance"] < amount: return await interaction.response.send_message(f"❌ {user.mention} kullanıcısının yeterli bakiyesi yok.", ephemeral=True)
                    reseller["balance"] -= amount; JsonManager.save_json("JSON/Data.json", data)
                    embed = discord.Embed(title="✅ Bakiye Çıkarma Başarılı", description=f"{user.mention} kullanıcısından {amount} bakiye alındı.", color=discord.Color.green())
                    embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
                    embed.add_field(name="İşlem Detayları", value=f"**Kullanıcı:** {user.name}\n**Çıkarılan Miktar:** {amount}\n**Tarih:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except Exception as e: await interaction.response.send_message(f"❌ Bir hata oluştu: {str(e)}", ephemeral=True)
     
     
            async def process_give_panel(self, interaction, user, days):
                try:
                    data = JsonManager.load_json("JSON/Data.json", {"resellers": []}); expiry_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
                    reseller = next((r for r in data["resellers"] if r["discord_id"] == str(user.id)), None)
                    if reseller:
                        reseller["reseller_access"] = True
                        if "panel_expiry" not in reseller: reseller["panel_expiry"] = expiry_date
                        else:
                            current_expiry = datetime.strptime(reseller["panel_expiry"], '%Y-%m-%d')
                            new_expiry = max(current_expiry, datetime.now()) + timedelta(days=days)
                            reseller["panel_expiry"] = new_expiry.strftime('%Y-%m-%d')
                    else: data["resellers"].append({"discord_name": user.name, "discord_id": str(user.id), "reseller_access": True, "panel_expiry": expiry_date, "balance": 0, "sales": []})
                    JsonManager.save_json("JSON/Data.json", data)
                    embed = discord.Embed(title="✅ Panel Erişimi Verildi", description=f"{user.mention} kullanıcısına {days} gün boyunca panel erişimi verildi.", color=discord.Color.green())
                    embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
                    embed.add_field(name="İşlem Detayları", value=f"**Kullanıcı:** {user.name}\n**Süre:** {days} gün\n**Bitiş Tarihi:** {expiry_date}\n**Tarih:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except Exception as e: await interaction.response.send_message(f"❌ Bir hata oluştu: {str(e)}", ephemeral=True)
       
       
            async def process_freeze_panel(self, interaction, user):
                try:
                    data = JsonManager.load_json("JSON/Data.json", {"resellers": []}); reseller = next((r for r in data["resellers"] if r["discord_id"] == str(user.id)), None)
                    if not reseller: return await interaction.response.send_message(f"❌ {user.mention} kullanıcısı reseller listesinde bulunamadı.", ephemeral=True)
                    reseller["reseller_access"] = False; JsonManager.save_json("JSON/Data.json", data)
                    embed = discord.Embed(title="🔒 Panel Erişimi Donduruldu", description=f"{user.mention} kullanıcısının panel erişimi donduruldu.", color=discord.Color.orange())
                    embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
                    embed.add_field(name="İşlem Detayları", value=f"**Kullanıcı:** {user.name}\n**Tarih:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except Exception as e: await interaction.response.send_message(f"❌ Bir hata oluştu: {str(e)}", ephemeral=True)
     
     
            async def process_unfreeze_panel(self, interaction, user):
                try:
                    data = JsonManager.load_json("JSON/Data.json", {"resellers": []}); reseller = next((r for r in data["resellers"] if r["discord_id"] == str(user.id)), None)
                    if not reseller: return await interaction.response.send_message(f"❌ {user.mention} kullanıcısı reseller listesinde bulunamadı.", ephemeral=True)
                    reseller["reseller_access"] = True; JsonManager.save_json("JSON/Data.json", data)
                    embed = discord.Embed(title="🔓 Panel Erişimi Açıldı", description=f"{user.mention} kullanıcısının panel erişimi açıldı.", color=discord.Color.green())
                    embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
                    embed.add_field(name="İşlem Detayları", value=f"**Kullanıcı:** {user.name}\n**Tarih:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except Exception as e: await interaction.response.send_message(f"❌ Bir hata oluştu: {str(e)}", ephemeral=True)
       
       
            async def process_freeze_all_panels(self, interaction):
                try:
                    data = JsonManager.load_json("JSON/Data.json", {"resellers": []})
                    if not data["resellers"]: return await interaction.response.send_message("❌ Hiçbir reseller bulunamadı.", ephemeral=True)
                    frozen_count = 0
                    for reseller in data["resellers"]:
                        if reseller.get("reseller_access", False): reseller["reseller_access"] = False; frozen_count += 1
                    JsonManager.save_json("JSON/Data.json", data)
                    embed = discord.Embed(title="❄️ Tüm Panel Erişimleri Donduruldu", description=f"Toplam {frozen_count} kullanıcının panel erişimi donduruldu.", color=discord.Color.orange())
                    embed.add_field(name="İşlem Detayları", value=f"**Dondurma Tarihi:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except Exception as e: await interaction.response.send_message(f"❌ Bir hata oluştu: {str(e)}", ephemeral=True)
          
          
            async def process_unfreeze_all_panels(self, interaction):
                try:
                    data = JsonManager.load_json("JSON/Data.json", {"resellers": []})
                    if not data["resellers"]: return await interaction.response.send_message("❌ Hiçbir reseller bulunamadı.", ephemeral=True)
                    unfrozen_count = 0
                    for reseller in data["resellers"]:
                        if not reseller.get("reseller_access", True): reseller["reseller_access"] = True; unfrozen_count += 1
                    JsonManager.save_json("JSON/Data.json", data)
                    embed = discord.Embed(title="🌡️ Tüm Panel Erişimleri Açıldı", description=f"Toplam {unfrozen_count} kullanıcının panel erişimi açıldı.", color=discord.Color.green())
                    embed.add_field(name="İşlem Detayları", value=f"**Açılma Tarihi:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except Exception as e: await interaction.response.send_message(f"❌ Bir hata oluştu: {str(e)}", ephemeral=True)
        await ctx.respond(embed=embed, view=AdminView(self), ephemeral=True)
def setup(bot): bot.add_cog(Admin(bot))
