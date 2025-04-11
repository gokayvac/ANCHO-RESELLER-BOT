import json, discord, os
from discord.ext import bridge, commands
from BotModules.JsonManager import JsonManager

class HwidReset(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        JsonManager.ensure_json_files()
        self.bot_config = JsonManager.load_json('JSON/Bot.json', {"prefix": "!", "token": "", "admin_ids": []})
        self.reseller_data = JsonManager.load_json('JSON/Data.json', {"resellers": []})
        self.products = JsonManager.load_json('JSON/Products.json', {"products": []})

    def is_reseller(self, user_id): return JsonManager.is_reseller(user_id)
            
    @bridge.bridge_command()
    async def hwidreset(self, ctx, license_key: str):
        if not self.is_reseller(ctx.author.id):
            await ctx.respond("Bu komutu sadece reseller'lar kullanabilir! ⛔", ephemeral=True)
            return

        class HwidResetView(discord.ui.View):
            def __init__(self, cog): super().__init__(); self.cog = cog
                
            @discord.ui.button(label="Evet, HWID Sıfırla", style=discord.ButtonStyle.primary, custom_id="confirm_hwid_reset")
            async def confirm(self, button, interaction):
                data = JsonManager.load_json('JSON/Data.json', {"resellers": []})
                reseller = next((r for r in data['resellers'] if str(interaction.user.id) == r['discord_id']), None)
                if 'sales' in reseller:
                    for sale in reseller['sales']:
                        if sale['license_key'] == license_key:
                            sale['hwid'] = ""
                            JsonManager.save_json('JSON/Data.json', data)
                            await interaction.response.send_message(f"✅ **{license_key}** lisans anahtarının HWID'si başarıyla sıfırlandı.", ephemeral=True)
                            return
                await interaction.response.send_message("Bu lisans anahtarı bulunamadı veya size ait değil.", ephemeral=True)
                
            @discord.ui.button(label="İptal", style=discord.ButtonStyle.secondary, custom_id="cancel_hwid_reset")
            async def cancel(self, button, interaction):
                await interaction.response.send_message("HWID sıfırlama işlemi iptal edildi.", ephemeral=True)
        
        confirm_embed = discord.Embed(title="🔄 HWID Sıfırlama Onayı", description=f"**{license_key}** lisans anahtarının HWID'sini sıfırlamak istediğinizden emin misiniz?", color=discord.Color.blue())
        await ctx.respond(embed=confirm_embed, view=HwidResetView(self), ephemeral=True)

def setup(bot): bot.add_cog(HwidReset(bot))