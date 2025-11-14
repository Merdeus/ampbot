import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from config import DISCORD_TOKEN, DATABASE_PATH
from database import Database
from http_client import HTTPClient

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
db = Database(DATABASE_PATH)
http_client = HTTPClient()

def is_admin():
    async def predicate(ctx):
        user_data = await db.get_user(ctx.author.id)
        if user_data and user_data['role'] == 'admin':
            return True
        await ctx.send("You need admin role to use this command.")
        return False
    return commands.check(predicate)

@bot.event
async def on_ready():
    print(f'{bot.user} has logged in!')
    await db.init_db()
    await db.add_history(f"Bot started and logged in as {bot.user}", None)
    
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')
    print('Database initialized!')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    user_data = await db.get_user(message.author.id)
    if not user_data:
        await db.add_user(message.author.id, 'user')
        await db.add_history(f"New user registered: {message.author.id} ({message.author})", message.author.id)
    
    await bot.process_commands(message)

@bot.command(name='ping')
async def ping(ctx):
    await ctx.send(f'Pong! Latency: {round(bot.latency * 1000)}ms')
    await db.add_history(f"Ping command used", ctx.author.id)

@bot.command(name='userinfo')
async def userinfo(ctx, user: discord.User = None):
    user = user or ctx.author
    user_data = await db.get_user(user.id)
    
    if user_data:
        color = user.color if isinstance(user, discord.Member) else discord.Color.blue()
        display_name = user.display_name if isinstance(user, discord.Member) else user.name
        embed = discord.Embed(title=f"User Info: {display_name}", color=color)
        embed.add_field(name="User ID", value=user_data['user_id'], inline=True)
        embed.add_field(name="Role", value=user_data['role'], inline=True)
        await ctx.send(embed=embed)
    else:
        display_name = user.display_name if isinstance(user, discord.Member) else user.name
        await ctx.send(f"No data found for {display_name}")

@bot.command(name='setrole')
@is_admin()
async def setrole(ctx, user: discord.User, role: str):
    if role not in ('user', 'admin'):
        await ctx.send("Role must be 'user' or 'admin'")
        return
    
    await db.add_user(user.id, role)
    await db.add_history(f"Role set: {user.id} -> {role}", ctx.author.id)
    await ctx.send(f"Set role of {user.mention} to {role}")

@bot.command(name='setpermission')
@is_admin()
async def setpermission(ctx, user: discord.User, instance_id: str, 
                       start: bool = False, stop: bool = False, status: bool = False):
    await db.set_instance_permission(user.id, instance_id, start, stop, status)
    await db.add_history(f"Permission set: user {user.id}, instance {instance_id}, start={start}, stop={stop}, status={status}", ctx.author.id)
    await ctx.send(f"Set permissions for {user.mention} on instance `{instance_id}`")

@bot.command(name='getpermission')
async def getpermission(ctx, user: discord.User = None, instance_id: str = None):
    user = user or ctx.author
    
    if instance_id:
        perm = await db.get_instance_permission(user.id, instance_id)
        if perm:
            embed = discord.Embed(title=f"Permissions for {user.name}", color=discord.Color.blue())
            embed.add_field(name="Instance ID", value=perm['instance_id'], inline=True)
            embed.add_field(name="Start", value="✓" if perm['start_permission'] else "✗", inline=True)
            embed.add_field(name="Stop", value="✓" if perm['stop_permission'] else "✗", inline=True)
            embed.add_field(name="Status", value="✓" if perm['status_permission'] else "✗", inline=True)
            if perm['additional_permissions']:
                embed.add_field(name="Additional", value=str(perm['additional_permissions']), inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"No permissions found for {user.mention} on instance `{instance_id}`")
    else:
        perms = await db.get_user_instance_permissions(user.id)
        if perms:
            embed = discord.Embed(title=f"All Permissions for {user.name}", color=discord.Color.blue())
            for perm in perms:
                perm_str = f"Start: {'✓' if perm['start_permission'] else '✗'} | "
                perm_str += f"Stop: {'✓' if perm['stop_permission'] else '✗'} | "
                perm_str += f"Status: {'✓' if perm['status_permission'] else '✗'}"
                embed.add_field(name=perm['instance_id'], value=perm_str, inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"No permissions found for {user.mention}")

@bot.command(name='addpermission')
@is_admin()
async def addpermission(ctx, user: discord.User, instance_id: str, permission_key: str, *, permission_value: str):
    try:
        import json
        value = json.loads(permission_value)
    except:
        value = permission_value
    
    await db.update_additional_permission(user.id, instance_id, permission_key, value)
    await db.add_history(f"Additional permission added: user {user.id}, instance {instance_id}, {permission_key}={value}", ctx.author.id)
    await ctx.send(f"Added permission `{permission_key}` = `{permission_value}` for {user.mention} on instance `{instance_id}`")

async def get_history_embed(user: discord.User = None, limit: int = 20):
    if limit > 100:
        limit = 100
    
    user_id = user.id if user else None
    history_entries = await db.get_history(limit, user_id)
    
    if history_entries:
        title = f"History"
        if user:
            title += f" for {user.name}"
        title += f" (Last {len(history_entries)} entries)"
        
        embed = discord.Embed(title=title, color=discord.Color.purple())
        
        history_lines = []
        for entry in history_entries[:10]:
            user_info = f"<@{entry['user_id']}>" if entry['user_id'] else "System"
            history_lines.append(f"`{entry['timestamp']}` [{user_info}] {entry['log']}")
        
        history_text = "\n".join(history_lines)
        if len(history_entries) > 10:
            history_text += f"\n... and {len(history_entries) - 10} more entries"
        
        embed.description = history_text
        return embed, history_entries
    return None, []

@bot.command(name='history')
async def history(ctx, *, args: str = None):
    user = None
    limit = 20
    
    if args:
        parts = args.split()
        for part in parts:
            if part.startswith('<@') and part.endswith('>'):
                try:
                    user_id = int(part[2:-1].replace('!', ''))
                    user = await bot.fetch_user(user_id)
                except:
                    pass
            elif part.isdigit():
                limit = int(part)
    
    embed, history_entries = await get_history_embed(user, limit)
    
    if embed:
        await ctx.send(embed=embed)
    else:
        if user:
            await ctx.send(f"No history entries found for {user.mention}")
        else:
            await ctx.send("No history entries found")

@bot.tree.command(name="history", description="View bot history, optionally filtered by user")
@app_commands.describe(
    user="Filter history by a specific user",
    limit="Number of entries to show (1-100)"
)
async def history_slash(interaction: discord.Interaction, 
                       user: discord.User = None, 
                       limit: app_commands.Range[int, 1, 100] = 20):
    embed, history_entries = await get_history_embed(user, limit)
    
    if embed:
        await interaction.response.send_message(embed=embed)
    else:
        if user:
            await interaction.response.send_message(f"No history entries found for {user.mention}", ephemeral=True)
        else:
            await interaction.response.send_message("No history entries found", ephemeral=True)

@bot.command(name='httpget')
async def httpget(ctx, url: str):
    try:
        await ctx.send(f"Fetching {url}...")
        response = await http_client.get_async(url)
        
        embed = discord.Embed(title="HTTP GET Response", color=discord.Color.blue())
        embed.add_field(name="Status Code", value=response['status'], inline=True)
        
        data_str = str(response['data'])
        if len(data_str) > 1000:
            data_str = data_str[:1000] + "... (truncated)"
        
        embed.add_field(name="Response Data", value=f"```json\n{data_str}\n```", inline=False)
        await ctx.send(embed=embed)
        await db.add_history(f"HTTP GET request to {url}", ctx.author.id)
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")
        await db.add_history(f"HTTP GET error: {str(e)}", ctx.author.id)

@bot.command(name='httppost')
async def httppost(ctx, url: str, *, json_data: str = None):
    try:
        import json
        data = json.loads(json_data) if json_data else {}
        
        await ctx.send(f"Posting to {url}...")
        response = await http_client.post_async(url, json=data)
        
        embed = discord.Embed(title="HTTP POST Response", color=discord.Color.green())
        embed.add_field(name="Status Code", value=response['status'], inline=True)
        
        data_str = str(response['data'])
        if len(data_str) > 1000:
            data_str = data_str[:1000] + "... (truncated)"
        
        embed.add_field(name="Response Data", value=f"```json\n{data_str}\n```", inline=False)
        await ctx.send(embed=embed)
        await db.add_history(f"HTTP POST request to {url}", ctx.author.id)
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")
        await db.add_history(f"HTTP POST error: {str(e)}", ctx.author.id)

@bot.command(name='help_custom')
async def help_custom(ctx):
    embed = discord.Embed(title="Bot Commands", color=discord.Color.orange())
    embed.add_field(name="!ping", value="Check bot latency", inline=False)
    embed.add_field(name="!userinfo [user]", value="Get user information", inline=False)
    embed.add_field(name="!setrole <user> <role>", value="Set user role (admin only)", inline=False)
    embed.add_field(name="!setpermission <user> <instance_id> [start] [stop] [status]", value="Set instance permissions (admin only)", inline=False)
    embed.add_field(name="!getpermission [user] [instance_id]", value="Get user permissions", inline=False)
    embed.add_field(name="!addpermission <user> <instance_id> <key> <value>", value="Add additional permission (admin only)", inline=False)
    embed.add_field(name="!history [user] [limit]", value="View bot history, optionally filtered by user (max 100)", inline=False)
    embed.add_field(name="!httpget <url>", value="Make an HTTP GET request", inline=False)
    embed.add_field(name="!httppost <url> [json]", value="Make an HTTP POST request", inline=False)
    await ctx.send(embed=embed)

def run_interaction_server():
    from interaction_handler import app, set_db_instance, set_bot_instance
    from config import INTERACTION_ENDPOINT_PORT
    
    set_db_instance(db)
    set_bot_instance(bot)
    
    print(f'Starting interaction endpoint server on port {INTERACTION_ENDPOINT_PORT}...')
    app.run(host='0.0.0.0', port=INTERACTION_ENDPOINT_PORT, debug=False, use_reloader=False)

if __name__ == '__main__':
    import threading
    
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN not found in environment variables!")
    else:
        interaction_thread = threading.Thread(target=run_interaction_server, daemon=True)
        interaction_thread.start()
        print('Interaction endpoint server started in background thread')
        
        bot.run(DISCORD_TOKEN)
