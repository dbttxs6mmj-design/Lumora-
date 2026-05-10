import { Bot } from 'grammy'
import Anthropic from '@anthropic-ai/sdk'
import { config } from 'dotenv'

config()

const bot = new Bot(process.env.TELEGRAM_BOT_TOKEN)
const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })

const sessions = new Map()

function getHistory(userId) {
  if (!sessions.has(userId)) sessions.set(userId, [])
  return sessions.get(userId)
}

bot.command('start', ctx =>
  ctx.reply('你好！我是 Lumora AI，有什麼我可以幫你嗎？\n\n/clear 清除對話記憶')
)

bot.command('clear', ctx => {
  sessions.delete(ctx.from.id)
  return ctx.reply('✅ 對話記憶已清除。')
})

bot.on('message:text', async ctx => {
  const history = getHistory(ctx.from.id)
  history.push({ role: 'user', content: ctx.message.text })
  if (history.length > 40) history.splice(0, 2)

  await ctx.replyWithChatAction('typing')

  try {
    const res = await anthropic.messages.create({
      model: 'claude-sonnet-4-6',
      max_tokens: 2048,
      system: '你是 Lumora AI，一位智慧、有溫度的助手。預設用繁體中文回應，但若使用者用其他語言則跟著切換。',
      messages: history,
    })

    const reply = res.content[0].text
    history.push({ role: 'assistant', content: reply })
    await ctx.reply(reply)
  } catch (err) {
    console.error(err)
    await ctx.reply('出了點問題，請稍後再試。')
  }
})

bot.start()
console.log('Lumora bot started')
