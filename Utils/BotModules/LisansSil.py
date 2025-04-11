import json, discord, os
from discord.ext import bridge, commands
from datetime import datetime, timedelta
from BotModules.JsonManager import JsonManager

class LisansSil(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        JsonManager.ensure_json_files()
        self.bot_config = JsonManager.load_json('JSON/Bot.json', {"prefix": "!", "token": "", "admin_ids": []})
        self.reseller_data = JsonManager.load_json('JSON/Data.json', {"resellers": []})
        self.products = JsonManager.load_json('JSON/Products.json', {"products": []})

    def is_reseller(self, user_id): return JsonManager.is_reseller(user_id)
            
    @bridge.bridge_command()
    async def lisanssil(self, ctx, license_key: str):
        if not self.is_reseller(ctx.author.id):
            await ctx.respond("Bu komutu sadece reseller'lar kullanabilir! ⛔", ephemeral=True)
            return

        class DeleteView(discord.ui.View):
            def __init__(self, cog): super().__init__(); self.cog = cog
                
            @discord.ui.button(label="Evet, Lisansı Sil", style=discord.ButtonStyle.danger, custom_id="confirm_delete")
            async def confirm(self, button, interaction):
                data = JsonManager.load_json('JSON/Data.json', {"resellers": []})
                reseller = next((r for r in data['resellers'] if str(interaction.user.id) == r['discord_id']), None)
                if 'sales' in reseller:
                    for sale in reseller['sales']:
                        if sale['license_key'] == license_key:
                            sale['status'] = "deleted"
                            JsonManager.save_json('JSON/Data.json', data)
                            await interaction.response.send_message(f"✅ **{license_key}** lisans anahtarı başarıyla silindi.", ephemeral=True)
                            return
                await interaction.response.send_message("Bu lisans anahtarı bulunamadı veya size ait değil.", ephemeral=True)
                
            @discord.ui.button(label="İptal", style=discord.ButtonStyle.secondary, custom_id="cancel_delete")
            async def cancel(self, button, interaction): await interaction.response.send_message("Lisans silme işlemi iptal edildi.", ephemeral=True)
        
        confirm_embed = discord.Embed(title="⚠️ Lisans Silme Onayı", description=f"**{license_key}** lisans anahtarını silmek istediğinizden emin misiniz?\n\nBu işlem geri alınamaz!", color=discord.Color.red())
        await ctx.respond(embed=confirm_embed, view=DeleteView(self), ephemeral=True)

def setup(bot): bot.add_cog(LisansSil(bot))