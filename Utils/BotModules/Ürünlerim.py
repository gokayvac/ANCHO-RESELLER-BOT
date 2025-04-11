import json, discord, os
from discord.ext import bridge, commands
from datetime import datetime, timedelta
from BotModules.JsonManager import JsonManager

class Ürünlerim(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        JsonManager.ensure_json_files()
        self.bot_config = JsonManager.load_json('JSON/Bot.json', {"prefix": "!", "token": "", "admin_ids": []})
        self.reseller_data = JsonManager.load_json('JSON/Data.json', {"resellers": []})
        self.products = JsonManager.load_json('JSON/Products.json', {"products": []})

    def is_reseller(self, user_id): return JsonManager.is_reseller(user_id)

    def send_notification(self, user_id, message):
        user = self.bot.get_user(user_id)
        if user:
            try: self.bot.loop.create_task(user.send(message))
            except Exception as e: print(f"Failed to send notification to {user_id}: {e}")

    def has_panel_access(self, user_id):
        try:
            with open('JSON/Data.json', 'r') as f:
                data = json.load(f)
                reseller = next((r for r in data['resellers'] if str(user_id) == r['discord_id']), None)
                return reseller and reseller.get('reseller_access', False)
        except: return False

    @bridge.bridge_command()
    async def ürünlerim(self, ctx):
        if not self.is_reseller(ctx.author.id):
            await ctx.respond("Bu komutu sadece reseller'lar kullanabilir! ⛔", ephemeral=True)
            return

        if not self.has_panel_access(ctx.author.id):
            await ctx.respond("Panel erişiminiz bulunmuyor. ⛔", ephemeral=True)
            return
        
        with open('JSON/Data.json', 'r') as f: data = json.load(f)
        with open('JSON/Products.json', 'r') as f: products_data = json.load(f)
        
        reseller = next((r for r in data['resellers'] if str(ctx.author.id) == r['discord_id']), None)
        if not reseller:
            await ctx.respond("Reseller bilgileriniz bulunamadı. ❌", ephemeral=True)
            return
        
        embed = discord.Embed(title="Ürün Listem", color=discord.Color.blue())
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        embed.set_footer(text=f"{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        elimde_olanlar = []
        if 'sales' in reseller:
            for sale in reseller['sales']:
                if sale.get('customer_id') == reseller['discord_id']:
                    product_id = sale.get('product_id')
                    product = next((p for p in products_data['products'] if p['id'] == product_id), None)
                    if product:
                        status = "✅ Aktif" if sale.get('status') != "deleted" else "❌ Silindi"
                        elimde_olanlar.append(f"• {product['name']} - {sale.get('license_key')} - {status}")
        
        if elimde_olanlar:
            chunks, current_chunk, current_length = [], [], 0
            for item in elimde_olanlar:
                if current_length + len(item) + 1 > 1000:
                    chunks.append("\n".join(current_chunk))
                    current_chunk, current_length = [item], len(item)
                else:
                    current_chunk.append(item)
                    current_length += len(item) + 1
            if current_chunk: chunks.append("\n".join(current_chunk))
            for i, chunk in enumerate(chunks):
                field_name = "📦 Elimde Olanlar" if i == 0 else "📦 Elimde Olanlar (devam)"
                embed.add_field(name=field_name, value=chunk, inline=False)
        
        sattiklarim = []
        if 'sales' in reseller:
            for sale in reseller['sales']:
                if sale.get('customer_id') != reseller['discord_id']:
                    product_id = sale.get('product_id')
                    product = next((p for p in products_data['products'] if p['id'] == product_id), None)
                    if product:
                        status = "✅ Aktif" if sale.get('status') != "deleted" else "❌ Silindi"
                        customer_name = sale.get('customer_name', 'Bilinmeyen Müşteri')
                        expiry = sale.get('expiry_date', 'Belirtilmemiş')
                        sattiklarim.append(f"• {product['name']} - {sale.get('license_key')} - {status}\n  └ Müşteri: {customer_name} | Bitiş: {expiry}")
        
        if sattiklarim:
            chunks, current_chunk, current_length = [], [], 0
            for item in sattiklarim:
                if current_length + len(item) + 1 > 1000:
                    chunks.append("\n".join(current_chunk))
                    current_chunk, current_length = [item], len(item)
                else:
                    current_chunk.append(item)
                    current_length += len(item) + 1
            if current_chunk: chunks.append("\n".join(current_chunk))
            for i, chunk in enumerate(chunks):
                field_name = "💰 Sattıklarım" if i == 0 else "💰 Sattıklarım (devam)"
                embed.add_field(name=field_name, value=chunk, inline=False)
        
        if not embed.fields: embed.description = "Henüz hiç ürününüz veya satışınız bulunmuyor."
        
        class ProductsManageView(discord.ui.View):
            def __init__(self, cog):
                super().__init__(timeout=180)
                self.cog = cog
                self.reseller_id = None
                self.reseller_data = None
            
            @discord.ui.button(label="Yeni Ürün Al", style=discord.ButtonStyle.green, custom_id="buy_new_product")
            async def buy_new_product(self, button, interaction):
                product_view = ProductSelectionView(self.cog)
                await interaction.response.send_message("Satın almak istediğiniz ürünü seçin:", view=product_view, ephemeral=True)
            
            @discord.ui.button(label="Ürün Transfer Et", style=discord.ButtonStyle.blurple, custom_id="transfer_product")
            async def transfer_product(self, button, interaction):
                select_menu = ProductTransferSelect(self.cog, interaction.user.id)
                transfer_view = discord.ui.View()
                transfer_view.add_item(select_menu)
                await interaction.response.send_message("Transfer etmek istediğiniz ürünü seçin:", view=transfer_view, ephemeral=True)
            
            @discord.ui.button(label="Lisans Yönetimi", style=discord.ButtonStyle.gray, custom_id="manage_licenses")
            async def manage_licenses(self, button, interaction):
                license_embed = discord.Embed(title="Lisans Yönetimi", description="Lisanslarınızı yönetmek için aşağıdaki seçeneklerden birini seçin.", color=discord.Color.blue())
                await interaction.response.send_message(embed=license_embed, view=LicenseManagementView(self.cog), ephemeral=True)
        
        class ProductSelectionView(discord.ui.View):
            def __init__(self, cog):
                super().__init__(timeout=180)
                self.cog = cog
                with open('JSON/Products.json', 'r') as f: products_data = json.load(f)
                options = [discord.SelectOption(label=product['name'], value=product['id'], description=f"Fiyat: ${product.get('price', 0):.2f}") for product in products_data['products']]
                self.product_select = discord.ui.Select(placeholder="Satın almak istediğiniz ürünü seçin", options=options, custom_id="product_selection")
                self.product_select.callback = self.on_product_select
                self.add_item(self.product_select)
            
            async def on_product_select(self, interaction):
                modal = QuantityModal(self.cog, self.product_select.values[0])
                await interaction.response.send_modal(modal)
        
        class QuantityModal(discord.ui.Modal):
            def __init__(self, cog, product_id):
                super().__init__(title="Ürün Miktarı")
                self.cog = cog
                self.product_id = product_id
                with open('JSON/Products.json', 'r') as f: products_data = json.load(f)
                product = next((p for p in products_data['products'] if p['id'] == product_id), None)
                product_name = product['name'] if product else "Ürün"
                self.quantity = discord.ui.InputText(label=f"{product_name} - Miktar", placeholder="Örn: 1", value="1", required=True, min_length=1, max_length=2)
                self.add_item(self.quantity)
            
            async def callback(self, interaction):
                try:
                    quantity = int(self.quantity.value)
                    if quantity <= 0:
                        await interaction.response.send_message("Geçersiz miktar. Lütfen pozitif bir sayı girin.", ephemeral=True)
                        return
                    
                    with open('JSON/Data.json', 'r') as f: data = json.load(f)
                    with open('JSON/Products.json', 'r') as f: products_data = json.load(f)
                    
                    reseller = next((r for r in data['resellers'] if str(interaction.user.id) == r['discord_id']), None)
                    product = next((p for p in products_data['products'] if p['id'] == self.product_id), None)
                    
                    if not product:
                        await interaction.response.send_message("Ürün bulunamadı.", ephemeral=True)
                        return

                    if product['stock'] <= 0:
                        await interaction.response.send_message("⚠️ Bu ürün şu anda stokta bulunmamaktadır.", ephemeral=True)
                        return
                        
                    if product['stock'] < quantity:
                        await interaction.response.send_message(f"⚠️ Yetersiz stok! İstenen: {quantity}, Mevcut stok: {product['stock']}", ephemeral=True)
                        return
                    
                    total_cost = product['price'] * quantity
                    if reseller['balance'] < total_cost:
                        await interaction.response.send_message(f"Yetersiz bakiye! Gereken: ${total_cost:.2f}, Mevcut: ${reseller['balance']:.2f}", ephemeral=True)
                        return
                    
                    reseller['balance'] -= total_cost
                    if 'sales' not in reseller: reseller['sales'] = []
                    
                    product['stock'] -= quantity
                    
                    licenses = []
                    for i in range(quantity):
                        license_key = f"LIC-{interaction.user.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{i}"
                        expiry_date = (datetime.now() + timedelta(days=product['duration_days'])).strftime("%Y-%m-%d %H:%M:%S")
                        sale = {
                            "product_id": product['id'],
                            "license_key": license_key,
                            "purchase_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "expiry_date": expiry_date,
                            "customer_id": str(interaction.user.id),
                            "customer_name": interaction.user.name,
                            "status": "active",
                            "hwid": ""
                        }
                        reseller['sales'].append(sale)
                        licenses.append(license_key)
                    
                    if 'balance_history' not in reseller: reseller['balance_history'] = []
                    reseller['balance_history'].append({
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "amount": -total_cost,
                        "type": "purchase",
                        "description": f"{quantity}x {product['name']} satın alındı"
                    })
                    
                    with open('JSON/Data.json', 'w') as f: json.dump(data, f, indent=4)
                    with open('JSON/Products.json', 'w') as f: json.dump(products_data, f, indent=4)
                    
                    embed = discord.Embed(title="✅ Satın Alma Başarılı", color=discord.Color.green())
                    embed.add_field(name="Ürün", value=product['name'], inline=True)
                    embed.add_field(name="Miktar", value=str(quantity), inline=True)
                    embed.add_field(name="Toplam Tutar", value=f"${total_cost:.2f}", inline=True)
                    embed.add_field(name="Kalan Bakiye", value=f"${reseller['balance']:.2f}", inline=True)
                    embed.add_field(name="Kalan Stok", value=str(product['stock']), inline=True)
                    embed.add_field(name="Lisans Anahtarları", value="\n".join(licenses), inline=False)
                    
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    self.cog.send_notification(interaction.user.id, f"Başarılı bir şekilde {quantity}x {product['name']} satın aldınız.")
                except ValueError:
                    await interaction.response.send_message("Geçersiz miktar. Lütfen bir sayı girin.", ephemeral=True)
        
        class ProductTransferSelect(discord.ui.Select):
            def __init__(self, cog, user_id):
                self.cog = cog
                with open('JSON/Data.json', 'r') as f: data = json.load(f)
                with open('JSON/Products.json', 'r') as f: products_data = json.load(f)
                reseller = next((r for r in data['resellers'] if str(user_id) == r['discord_id']), None)
                options = []
                if reseller and 'sales' in reseller:
                    for sale in reseller['sales']:
                        if sale.get('customer_id') == reseller['discord_id'] and sale.get('status') != "deleted":
                            product = next((p for p in products_data['products'] if p['id'] == sale.get('product_id')), None)
                            if product:
                                options.append(discord.SelectOption(label=f"{product['name']} - {sale.get('license_key')[:10]}...", value=sale.get('license_key'), description=f"Müşteri: {sale.get('customer_name', 'Bilinmeyen')[:15]}..."))
                if not options: options = [discord.SelectOption(label="Transfer edilebilecek ürün yok", value="none")]
                super().__init__(placeholder="Transfer edilecek ürünü seçin", options=options)
            
            async def callback(self, interaction):
                if self.values[0] == "none":
                    await interaction.response.send_message("Transfer edilebilecek ürününüz bulunmuyor.", ephemeral=True)
                    return
                
                modal = discord.ui.Modal(title="Ürün Transfer")
                recipient_id = discord.ui.InputText(label="Alıcı Discord ID", placeholder="Alıcının Discord ID'sini girin", required=True)
                modal.add_item(recipient_id)
                
                async def modal_callback(interaction):
                    try:
                        recipient_id_value = recipient_id.value.strip()
                        try:
                            recipient_user = await interaction.client.fetch_user(int(recipient_id_value))
                        except:
                            await interaction.response.send_message("Geçerli bir Discord kullanıcısı bulunamadı.", ephemeral=True)
                            return
                        
                        with open('JSON/Data.json', 'r') as f: data = json.load(f)
                        with open('JSON/Products.json', 'r') as f: products_data = json.load(f)
                        reseller = next((r for r in data['resellers'] if str(interaction.user.id) == r['discord_id']), None)
                        license_found, product_name = False, ""
                        license_key = self.values[0]
                        
                        if 'sales' in reseller:
                            for sale in reseller['sales']:
                                if sale.get('license_key') == license_key and sale.get('customer_id') == reseller['discord_id']:
                                    sale['customer_id'] = recipient_id_value
                                    sale['customer_name'] = recipient_user.name
                                    product = next((p for p in products_data['products'] if p['id'] == sale.get('product_id')), None)
                                    if product: product_name = product['name']
                                    license_found = True
                                    break
                        
                        if not license_found:
                            await interaction.response.send_message("Bu lisans anahtarı bulunamadı veya size ait değil.", ephemeral=True)
                            return
                        
                        with open('JSON/Data.json', 'w') as f: json.dump(data, f, indent=4)
                        
                        embed = discord.Embed(title="✅ Ürün Transferi Başarılı", color=discord.Color.green())
                        embed.add_field(name="Ürün", value=product_name, inline=True)
                        embed.add_field(name="Lisans", value=license_key, inline=True)
                        embed.add_field(name="Alıcı", value=f"{recipient_user.mention} ({recipient_user.name})", inline=True)
                        
                        try:
                            user_embed = discord.Embed(title="🎁 Yeni Ürün Aldınız!", color=discord.Color.green())
                            user_embed.add_field(name="Ürün", value=product_name, inline=True)
                            user_embed.add_field(name="Lisans", value=license_key, inline=True)
                            user_embed.add_field(name="Gönderen", value=f"{interaction.user.mention} ({interaction.user.name})", inline=True)
                            await recipient_user.send(embed=user_embed)
                        except:
                            embed.add_field(name="Not", value="Kullanıcıya DM gönderilemedi.", inline=False)
                        
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        self.cog.send_notification(interaction.user.id, f"Başarılı bir şekilde {product_name} ürününü {recipient_user.name} kullanıcısına transfer ettiniz.")
                    except Exception as e:
                        await interaction.response.send_message(f"Bir hata oluştu: {str(e)}", ephemeral=True)
                
                modal.callback = modal_callback
                await interaction.response.send_modal(modal)
        
        class LicenseManagementView(discord.ui.View):
            def __init__(self, cog):
                super().__init__(timeout=180)
                self.cog = cog
            
            @discord.ui.button(label="Lisans Bilgilerini Görüntüle", style=discord.ButtonStyle.primary)
            async def view_license(self, button: discord.ui.Button, interaction: discord.Interaction):
                with open('JSON/Data.json', 'r') as f: data = json.load(f)
                with open('JSON/Products.json', 'r') as f: products_data = json.load(f)
                reseller = next((r for r in data['resellers'] if str(interaction.user.id) == r['discord_id']), None)
                
                if not reseller or 'sales' not in reseller or not reseller['sales']:
                    await interaction.response.send_message("Hiç lisansınız bulunmuyor.", ephemeral=True)
                    return
                
                license_view = discord.ui.View()
                options = []
                
                for sale in reseller['sales']:
                    product = next((p for p in products_data['products'] if p['id'] == sale.get('product_id')), None)
                    product_name = product['name'] if product else "Bilinmeyen Ürün"
                    options.append(discord.SelectOption(label=f"{product_name} - {sale.get('license_key')[:10]}...", value=sale.get('license_key'), description=f"Müşteri: {sale.get('customer_name', 'Bilinmeyen')[:15]}..."))
                
                if len(options) > 25: options = options[:25]
                license_select = LicenseInfoSelect(options)
                license_view.add_item(license_select)
                await interaction.response.send_message("Detaylarını görmek istediğiniz lisansı seçin:", view=license_view, ephemeral=True)
            
            @discord.ui.button(label="HWID Sıfırla", style=discord.ButtonStyle.danger)
            async def reset_hwid(self, button: discord.ui.Button, interaction: discord.Interaction):
                with open('JSON/Data.json', 'r') as f: data = json.load(f)
                with open('JSON/Products.json', 'r') as f: products_data = json.load(f)
                reseller = next((r for r in data['resellers'] if str(interaction.user.id) == r['discord_id']), None)
                
                if not reseller or 'sales' not in reseller or not reseller['sales']:
                    await interaction.response.send_message("Hiç lisansınız bulunmuyor.", ephemeral=True)
                    return
                
                hwid_view = discord.ui.View()
                options = []
                
                for sale in reseller['sales']:
                    if sale.get('status') == "active":
                        product = next((p for p in products_data['products'] if p['id'] == sale.get('product_id')), None)
                        product_name = product['name'] if product else "Bilinmeyen Ürün"
                        options.append(discord.SelectOption(label=f"{product_name} - {sale.get('license_key')[:10]}...", value=sale.get('license_key'), description=f"HWID: {'Ayarlanmış' if sale.get('hwid') else 'Boş'}"))
                
                if not options:
                    await interaction.response.send_message("HWID sıfırlanabilecek aktif lisansınız bulunmuyor.", ephemeral=True)
                    return
                
                if len(options) > 25: options = options[:25]
                hwid_select = HwidResetSelect(options)
                hwid_view.add_item(hwid_select)
                await interaction.response.send_message("HWID'sini sıfırlamak istediğiniz lisansı seçin:", view=hwid_view, ephemeral=True)
        
        class LicenseInfoSelect(discord.ui.Select):
            def __init__(self, options):
                super().__init__(placeholder="Lisans seçin", options=options)
            
            async def callback(self, interaction):
                with open('JSON/Data.json', 'r') as f: data = json.load(f)
                with open('JSON/Products.json', 'r') as f: products_data = json.load(f)
                reseller = next((r for r in data['resellers'] if str(interaction.user.id) == r['discord_id']), None)
                license_key = self.values[0]
                license_info, product_info = None, None
                
                if reseller and 'sales' in reseller:
                    for sale in reseller['sales']:
                        if sale.get('license_key') == license_key:
                            license_info = sale
                            product_info = next((p for p in products_data['products'] if p['id'] == sale.get('product_id')), None)
                            break
                
                if not license_info:
                    await interaction.response.send_message("Lisans bilgisi bulunamadı.", ephemeral=True)
                    return
                
                embed = discord.Embed(title="🔑 Lisans Bilgileri", color=discord.Color.blue())
                embed.add_field(name="Ürün", value=product_info['name'] if product_info else "Bilinmeyen", inline=True)
                embed.add_field(name="Lisans Anahtarı", value=license_info.get('license_key', "Bilinmeyen"), inline=True)
                embed.add_field(name="Durum", value="✅ Aktif" if license_info.get('status') == "active" else "❌ Pasif", inline=True)
                embed.add_field(name="Müşteri", value=license_info.get('customer_name', "Bilinmeyen"), inline=True)
                embed.add_field(name="Satın Alma Tarihi", value=license_info.get('purchase_date', "Bilinmeyen"), inline=True)
                embed.add_field(name="Bitiş Tarihi", value=license_info.get('expiry_date', "Bilinmeyen"), inline=True)
                embed.add_field(name="HWID", value=license_info.get('hwid', "Ayarlanmamış"), inline=True)
                await interaction.response.send_message(embed=embed, ephemeral=True)
        
        class HwidResetSelect(discord.ui.Select):
            def __init__(self, options):
                super().__init__(placeholder="HWID sıfırlanacak lisansı seçin", options=options)
            
            async def callback(self, interaction):
                license_key = self.values[0]
                confirm_view = discord.ui.View()
                confirm_view.add_item(discord.ui.Button(label="Evet, HWID Sıfırla", style=discord.ButtonStyle.danger, custom_id=f"confirm_hwid_reset_{license_key}"))
                confirm_view.add_item(discord.ui.Button(label="İptal", style=discord.ButtonStyle.secondary, custom_id="cancel_hwid_reset"))
                
                for item in confirm_view.children:
                    if isinstance(item, discord.ui.Button):
                        if item.custom_id.startswith("confirm_hwid_reset_"): item.callback = lambda i, key=license_key: self.confirm_hwid_reset(i, key)
                        elif item.custom_id == "cancel_hwid_reset": item.callback = self.cancel_hwid_reset
                
                await interaction.response.send_message(f"**{license_key}** lisansının HWID'sini sıfırlamak istediğinizden emin misiniz?", view=confirm_view, ephemeral=True)
            
            async def confirm_hwid_reset(self, interaction, license_key):
                with open('JSON/Data.json', 'r') as f: data = json.load(f)
                reseller = next((r for r in data['resellers'] if str(interaction.user.id) == r['discord_id']), None)
                license_found = False
                
                if reseller and 'sales' in reseller:
                    for sale in reseller['sales']:
                        if sale.get('license_key') == license_key:
                            sale['hwid'] = ""
                            license_found = True
                            break
                
                if not license_found:
                    await interaction.response.send_message("Bu lisans anahtarı bulunamadı veya size ait değil.", ephemeral=True)
                    return
                
                with open('JSON/Data.json', 'w') as f: json.dump(data, f, indent=4)
                await interaction.response.send_message(f"✅ **{license_key}** lisansının HWID'si başarıyla sıfırlandı.", ephemeral=True)
                self.cog.send_notification(interaction.user.id, f"Başarılı bir şekilde {license_key} lisansının HWID'sini sıfırladınız.")
            
            async def cancel_hwid_reset(self, interaction):
                await interaction.response.send_message("HWID sıfırlama işlemi iptal edildi.", ephemeral=True)
        
        view = ProductsManageView(self)
        await ctx.respond(embed=embed, view=view, ephemeral=True)

def setup(bot):
    bot.add_cog(Ürünlerim(bot))
