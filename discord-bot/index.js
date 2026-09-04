const { Client, GatewayIntentBits, ChannelType, PermissionFlagsBits } = require('discord.js');
const http = require('http');

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMembers,
    GatewayIntentBits.GuildPresences,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildModeration,
    GatewayIntentBits.GuildVoiceStates,
  ],
});

function firstGuild() {
  const guild = client.guilds.cache.first();
  if (!guild) throw new Error('Not in a guild');
  return guild;
}

function findTextChannel(guild, ref) {
  if (ref) {
    const byId = guild.channels.cache.get(ref);
    if (byId && byId.isTextBased()) return byId;
    const byName = guild.channels.cache.find(
      (ch) => ch.isTextBased() && ch.name.toLowerCase() === String(ref).toLowerCase()
    );
    if (byName) return byName;
  }
  return guild.channels.cache.find((ch) => ch.type === ChannelType.GuildText);
}

async function findMember(guild, ref) {
  if (!ref) throw new Error('Missing user');
  try {
    return await guild.members.fetch(ref);
  } catch (e) {
    const lower = String(ref).toLowerCase();
    const m = guild.members.cache.find(
      (x) => x.user.tag.toLowerCase() === lower || x.user.username.toLowerCase() === lower
    );
    if (m) return m;
    throw new Error('Member not found: ' + ref);
  }
}

async function findRole(guild, ref) {
  if (!ref) throw new Error('Missing role');
  const byId = guild.roles.cache.get(ref);
  if (byId) return byId;
  const byName = guild.roles.cache.find((r) => r.name.toLowerCase() === String(ref).toLowerCase());
  if (byName) return byName;
  throw new Error('Role not found: ' + ref);
}

client.once('clientReady', async () => {
  console.log('Logged in as ' + client.user.tag);
  try {
    await client.user.setPresence({
      activities: [{ name: 'Admin Control', type: 2 }],
      status: 'online',
    });
  } catch (e) {
    console.log('Presence failed: ' + e.message);
  }
  console.log('Bot ready, control server starting');
  startControlServer();
});

function startControlServer() {
  const port = 3000;
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://localhost');
    if (req.method === 'GET' && url.pathname === '/auth/callback') {
      const code = url.searchParams.get('code');
      const guildId = url.searchParams.get('guild_id');
      console.log('OAuth callback: guild=' + guildId + ' code=' + (code ? code.substring(0, 8) + '...' : 'none'));
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end('<h1>BlackGrid Bot added</h1><p>Guild: ' + (guildId || 'unknown') + '</p><p>You can close this tab.</p>');
      return;
    }
    if (req.method === 'GET' && url.pathname === '/') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true, bot: client.user ? client.user.tag : 'starting' }));
      return;
    }
    if (req.method !== 'POST' || url.pathname !== '/discord-command') {
      res.writeHead(404);
      res.end('Not found');
      return;
    }
    let body = '';
    req.on('data', (chunk) => { body += chunk; });
    req.on('end', async () => {
      let c;
      try {
        c = JSON.parse(body);
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Invalid JSON' }));
        return;
      }
      const ok = (obj) => {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(Object.assign({ success: true }, obj)));
      };
      const fail = (code, msg) => {
        res.writeHead(code, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: msg }));
      };
      try {
        const guild = firstGuild();
        switch (c.type) {
          case 'send-message': {
            const ch = findTextChannel(guild, c.channel);
            if (!ch || !c.message) return fail(404, 'Channel not found');
            const sent = await ch.send(c.message);
            console.log('Message sent to #' + ch.name);
            return ok({ message: 'Message sent', id: sent.id, channel: ch.name });
          }
          case 'get-messages': {
            const ch = findTextChannel(guild, c.channel);
            if (!ch) return fail(404, 'Channel not found');
            const msgs = await ch.messages.fetch({ limit: Math.min(c.limit || 20, 100) });
            return ok({
              channel: ch.name,
              messages: [...msgs.values()].reverse().map((m) => ({
                id: m.id, author: m.author.tag, content: m.content, at: m.createdAt,
              })),
            });
          }
          case 'list-channels':
            return ok({
              channels: [...guild.channels.cache.values()].map((ch) => ({
                id: ch.id, name: ch.name, type: ch.type,
              })),
            });
          case 'list-members': {
            const members = await guild.members.fetch({ limit: 200 });
            return ok({
              members: [...members.values()].slice(0, c.limit || 50).map((m) => ({
                id: m.user.id, tag: m.user.tag,
                roles: [...m.roles.cache.values()].map((r) => r.name),
              })),
            });
          }
          case 'list-roles':
            return ok({
              roles: [...guild.roles.cache.values()].map((r) => ({ id: r.id, name: r.name })),
            });
          case 'create-role': {
            const perms = Array.isArray(c.permissions)
              ? c.permissions.map((p) => PermissionFlagsBits[p]).filter(Boolean)
              : [PermissionFlagsBits.Administrator];
            const role = await guild.roles.create({
              name: c.roleName,
              permissions: perms,
              color: c.color || 0,
              hoist: c.hoist !== false,
              mentionable: c.mentionable === true,
              reason: 'Created via OpenCode control',
            });
            console.log('Created role: ' + role.name);
            return ok({ role: role.name, id: role.id });
          }
          case 'delete-role': {
            const role = await findRole(guild, c.role);
            await role.delete('Deleted via OpenCode control');
            return ok({ deleted: role.name });
          }
          case 'update-role': {
            const role = await findRole(guild, c.role);
            const patch = {};
            if (c.name) patch.name = c.name;
            if (typeof c.color === 'number') patch.color = c.color;
            if (typeof c.hoist === 'boolean') patch.hoist = c.hoist;
            if (typeof c.mentionable === 'boolean') patch.mentionable = c.mentionable;
            const updated = await role.edit(patch);
            console.log('Updated role: ' + updated.name);
            return ok({ role: updated.name, id: updated.id });
          }
          case 'assign-role': {
            const m = await findMember(guild, c.user);
            const r = await findRole(guild, c.role);
            await m.roles.add(r);
            return ok({ assigned: r.name + ' -> ' + m.user.tag });
          }
          case 'remove-role': {
            const m = await findMember(guild, c.user);
            const r = await findRole(guild, c.role);
            await m.roles.remove(r);
            return ok({ removed: r.name + ' -/-> ' + m.user.tag });
          }
          case 'create-channel': {
            const ch = await guild.channels.create({
              name: c.name,
              type: c.voice ? ChannelType.GuildVoice : ChannelType.GuildText,
              reason: 'Created via OpenCode control',
            });
            return ok({ channel: ch.name, id: ch.id });
          }
          case 'delete-channel': {
            const ch = findTextChannel(guild, c.channel) || guild.channels.cache.get(c.channel);
            if (!ch) return fail(404, 'Channel not found');
            await ch.delete('Deleted via OpenCode control');
            return ok({ deleted: ch.name });
          }
          case 'delete-message': {
            const ch = findTextChannel(guild, c.channel);
            if (!ch) return fail(404, 'Channel not found');
            const msg = await ch.messages.fetch(c.messageId);
            await msg.delete();
            return ok({ deleted: c.messageId });
          }
          case 'kick': {
            const m = await findMember(guild, c.user);
            await m.kick(c.reason || 'Kicked via OpenCode control');
            return ok({ kicked: m.user.tag });
          }
          case 'ban': {
            const m = await findMember(guild, c.user);
            await guild.members.ban(m.id, { reason: c.reason || 'Banned via OpenCode control' });
            return ok({ banned: m.user.tag });
          }
          case 'unban': {
            await guild.members.unban(c.user, c.reason || 'Unbanned via OpenCode control');
            return ok({ unbanned: c.user });
          }
          case 'timeout': {
            const m = await findMember(guild, c.user);
            await m.timeout((c.minutes || 10) * 60 * 1000, c.reason || 'Timed out via OpenCode');
            return ok({ timedOut: m.user.tag });
          }
          case 'guild-info': {
            const g = guild;
            return ok({
              guild: {
                id: g.id, name: g.name, memberCount: g.memberCount,
                channels: g.channels.cache.size, roles: g.roles.cache.size,
              },
            });
          }
          default:
            return fail(400, 'Unknown command type');
        }
      } catch (err) {
        console.error('Command failed: ' + err.message);
        return fail(500, err.message);
      }
    });
  });
  server.listen(port, () => console.log('Control server on port ' + port));
}

const token = process.env.DISCORD_BOT_TOKEN;
if (!token) {
  console.error('ERROR: DISCORD_BOT_TOKEN not set');
  process.exit(1);
}
client.login(token);
