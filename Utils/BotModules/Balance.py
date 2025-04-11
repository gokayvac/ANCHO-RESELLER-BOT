import json, discord, os
from discord.ext import bridge, commands
from datetime import datetime
from BotModules.JsonManager import JsonManager

class Balance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        JsonManager.ensure_json_files()
        self.bot_config = JsonManager.load_json('JSON/Bot.json', {"prefix": "!", "token": "", "admin_ids": []})
        self.reseller_data = JsonManager.load_json('JSON/Data.json', {"resellers": []})
        self.products = JsonManager.load_json('JSON/Products.json', {"products": []})

    def is_reseller(self, user_id):
        return JsonManager.is_reseller(user_id)
            
    @bridge.bridge_command()
    async def balance(self, ctx):
        if not self.is_reseller(ctx.author.id):
            await ctx.respond("Bu komutu sadece reseller'lar kullanabilir! ⛔", ephemeral=True)
            return
        with open('JSON/Data.json', 'r') as f: data = json.load(f)
        reseller = next((r for r in data['resellers'] if str(ctx.author.id) == r['discord_id']), None)
        embed = discord.Embed(title="💰 Reseller Bakiyesi", color=discord.Color.green())
        embed.add_field(name="Mevcut Bakiye", value=f"${reseller['balance']:.2f} 💵")
        
        class BalanceView(discord.ui.View):
            def __init__(self, cog): super().__init__(); self.cog = cog
                
            @discord.ui.button(label="Bakiye Yükle", style=discord.ButtonStyle.green, custom_id="load_balance")
            async def load_balance(self, button, interaction):
                modal = discord.ui.Modal(title="Bakiye Yükleme")
                modal.add_item(discord.ui.InputText(label="Miktar ($)", placeholder="Örn: 50.00"))
                
                async def modal_callback(interaction):
                    amount = float(modal.children[0].value)
                    with open('JSON/Data.json', 'r') as f: data = json.load(f)
                    reseller = next((r for r in data['resellers'] if str(interaction.user.id) == r['discord_id']), None)
                    with open('JSON/Bot.json', 'r') as f: bot_config = json.load(f)
                    log_channel_id = bot_config.get('channels', {}).get('bakiye_yukleme_log')
                    if log_channel_id:
                        try:
                            log_channel = self.cog.bot.get_channel(int(log_channel_id))
                            if log_channel:
                                class ApproveBalanceView(discord.ui.View):
                                    def __init__(self): super().__init__(timeout=None)
                                    
                                    @discord.ui.button(label="Onayla", style=discord.ButtonStyle.green, custom_id="approve_balance")
                                    async def approve_balance(self, button, approve_interaction):
                                        if not approve_interaction.user.guild_permissions.administrator:
                                            await approve_interaction.response.send_message("Bu işlemi sadece yöneticiler yapabilir!", ephemeral=True)
                                            return
                                        with open('JSON/Data.json', 'r') as f: updated_data = json.load(f)
                                        updated_reseller = next((r for r in updated_data['resellers'] if str(interaction.user.id) == r['discord_id']), None)
                                        if updated_reseller:
                                            updated_reseller['balance'] += amount
                                            if 'balance_history' not in updated_reseller: updated_reseller['balance_history'] = []
                                            updated_reseller['balance_history'].append({
                                                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                                "amount": amount,
                                                "type": "deposit",
                                                "description": f"Bakiye yükleme (Onaylayan: {approve_interaction.user.name})"
                                            })
                                            with open('JSON/Data.json', 'w') as f: json.dump(updated_data, f, indent=4)
                                            try:
                                                user = self.cog.bot.get_user(int(interaction.user.id))
                                                if user:
                                                    user_embed = discord.Embed(title="💰 Bakiye Yükleme Onaylandı", description=f"Bakiye yükleme talebiniz onaylandı!", color=discord.Color.green())
                                                    user_embed.add_field(name="Yüklenen Miktar", value=f"${amount:.2f}", inline=True)
                                                    user_embed.add_field(name="Yeni Bakiye", value=f"${updated_reseller['balance']:.2f}", inline=True)
                                                    await user.send(embed=user_embed)
                                            except: pass
                                            confirm_embed = discord.Embed(title="✅ Bakiye Yükleme Onaylandı", description=f"{interaction.user.mention} kullanıcısına ${amount:.2f} bakiye yüklendi.", color=discord.Color.green())
                                            await approve_interaction.response.send_message(embed=confirm_embed)
                                            for child in self.children: child.disabled = True
                                            await approve_interaction.message.edit(view=self)
                                        else: await approve_interaction.response.send_message("Kullanıcı bulunamadı!", ephemeral=True)
                                
                                log_embed = discord.Embed(title="💰 Bakiye Yükleme Talebi", description=f"{interaction.user.mention} ({interaction.user.name}) bakiye yüklemek istiyor.", color=discord.Color.gold())
                                log_embed.add_field(name="Kullanıcı ID", value=interaction.user.id, inline=True)
                                log_embed.add_field(name="İstenilen Miktar", value=f"${amount:.2f}", inline=True)
                                log_embed.add_field(name="Mevcut Bakiye", value=f"${reseller['balance']:.2f}", inline=True)
                                log_embed.set_thumbnail(url=interaction.user.display_avatar.url)
                                await log_channel.send(embed=log_embed, view=ApproveBalanceView())
                                await interaction.response.send_message("Bakiye yükleme talebiniz admin ekibine iletildi. Onaylandıktan sonra bakiyeniz güncellenecektir.", ephemeral=True)
                            else: await interaction.response.send_message("Bakiye yükleme talebi oluşturulurken bir hata oluştu. Lütfen yöneticiye başvurun.", ephemeral=True)
                        except Exception as e: await interaction.response.send_message(f"Bakiye yükleme talebi oluşturulurken bir hata oluştu: {str(e)}", ephemeral=True)
                    else: await interaction.response.send_message("Bakiye yükleme log kanalı ayarlanmamış. Lütfen yöneticiye başvurun.", ephemeral=True)
                
                modal.callback = modal_callback
                await interaction.response.send_modal(modal)
                
            @discord.ui.button(label="İşlem Geçmişi", style=discord.ButtonStyle.blurple, custom_id="balance_history")
            async def balance_history(self, button, interaction):
                with open('JSON/Data.json', 'r') as f: data = json.load(f)
                reseller = next((r for r in data['resellers'] if str(interaction.user.id) == r['discord_id']), None)
                embed = discord.Embed(title="💰 İşlem Geçmişi", color=discord.Color.blue())
                if 'balance_history' not in reseller or not reseller['balance_history']: embed.description = "Henüz İşlem bulunmuyor."
                else:
                    for i, transaction in enumerate(reseller['balance_history'][-10:]):
                        embed.add_field(name=f"{transaction['date']} - {transaction['type'].capitalize()}", value=f"${transaction['amount']:.2f} - {transaction['description']}", inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)
        
        await ctx.respond(embed=embed, view=BalanceView(self), ephemeral=True)

def setup(bot): bot.add_cog(Balance(bot))