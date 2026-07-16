import { expect, test } from '@playwright/test'

test('renders the agent workspace on desktop', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/')

  await expect(page.getByRole('heading', { name: '与南郭先生对话' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '南郭先生', exact: true })).toBeVisible()
  await expect(page.getByText('南郭乐团代表')).toBeVisible()
  await expect(page.getByText('Chat Agent')).toHaveCount(0)
  await expect(page.getByPlaceholder(/以后默认给我做纯音乐/)).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(1440)
  await page.screenshot({ path: '/tmp/nanguos-desktop.png', fullPage: true })
})

test('keeps controls readable on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')

  await expect(page.getByRole('heading', { name: '与南郭先生对话' })).toBeVisible()
  await page.getByRole('button', { name: '创作台' }).click()
  await expect(page.getByRole('button', { name: '召集乐团开始创作' })).toBeVisible()
  await expect(page.getByRole('combobox', { name: '流派' })).toBeVisible()
  await page.getByRole('combobox', { name: '流派' }).selectOption('电子')
  await page.getByRole('combobox', { name: '语言' }).selectOption('纯音乐')
  await page.getByRole('button', { name: '合成器' }).click()
  await expect(page.getByRole('button', { name: '合成器' })).toHaveAttribute('aria-pressed', 'true')
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  await page.screenshot({ path: '/tmp/nanguos-mobile.png', fullPage: true })
})

test('switches and manages isolated chat sessions', async ({ page }) => {
  const now = '2026-07-16T12:00:00Z'
  let sessions = [
    {
      id: 'session-one',
      title: '雨夜灵感',
      messages: [{ id: 'm1', role: 'user', content: '第一个会话的内容', created_at: now }],
      created_at: now,
      updated_at: now,
    },
    {
      id: 'session-two',
      title: '公路配乐',
      messages: [{ id: 'm2', role: 'user', content: '第二个会话的内容', created_at: now }],
      created_at: now,
      updated_at: now,
    },
  ]
  await page.route('http://127.0.0.1:8000/api/portfolio', (route) => route.fulfill({ json: [] }))
  await page.route('http://127.0.0.1:8000/api/sessions**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const sessionId = url.pathname.split('/').at(-1)
    if (url.pathname === '/api/sessions') {
      await route.fulfill({ json: sessions })
      return
    }
    const session = sessions.find((item) => item.id === sessionId)
    if (!session) {
      await route.fulfill({ status: 404, json: { detail: 'Session not found' } })
      return
    }
    if (request.method() === 'PATCH') {
      const payload = request.postDataJSON() as { title: string }
      session.title = payload.title
      await route.fulfill({ json: session })
      return
    }
    if (request.method() === 'DELETE') {
      sessions = sessions.filter((item) => item.id !== sessionId)
      await route.fulfill({ status: 204, body: '' })
      return
    }
    await route.fulfill({ json: session })
  })

  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/?session=session-one')
  await expect(page.getByText('第一个会话的内容')).toBeVisible()
  await page.getByRole('button', { name: /公路配乐/ }).click()
  await expect(page).toHaveURL(/session=session-two/)
  await expect(page.getByText('第二个会话的内容')).toBeVisible()
  await expect(page.getByText('第一个会话的内容')).toHaveCount(0)

  const activeRow = page.locator('.session-row.active')
  await activeRow.getByTitle('对话操作').click()
  await page.getByRole('button', { name: '重命名' }).click()
  await activeRow.getByRole('textbox').fill('新的公路配乐')
  await activeRow.getByTitle('保存').click()
  await expect(activeRow.getByText('新的公路配乐')).toBeVisible()

  page.once('dialog', (dialog) => dialog.accept())
  await activeRow.getByTitle('对话操作').click()
  await page.getByRole('button', { name: '删除' }).click()
  await expect(page).toHaveURL(/session=session-one/)
  await expect(page.getByText('第一个会话的内容')).toBeVisible()

  await page.locator('.new-project').click()
  await expect(page).not.toHaveURL(/session=/)
  await expect(page.getByText('从一个想法开始')).toBeVisible()
  await page.getByRole('button', { name: /雨夜灵感/ }).click()

  await page.setViewportSize({ width: 390, height: 844 })
  await page.getByTitle('查看对话').click()
  await expect(page.getByRole('dialog', { name: '对话列表' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  await page.screenshot({ path: '/tmp/nanguos-sessions-mobile.png', fullPage: true })
})

test('renders a persisted workflow run and playable result inside chat', async ({ page }) => {
  const now = '2026-07-16T12:00:00Z'
  const workflowRun = {
    project_id: 'project-chat',
    run_id: 'run-chat',
    title: '霓虹雨夜',
    preset: 'electronic_instrumental',
  }
  const session = {
    id: 'session-workflow',
    title: '霓虹雨夜',
    active_project_id: 'project-chat',
    messages: [
      { id: 'm1', role: 'user', content: '生成一首雨夜电子纯音乐', created_at: now },
      { id: 'm2', role: 'assistant', content: '乐团已经开始创作。', workflow_run: workflowRun, created_at: now },
    ],
    created_at: now,
    updated_at: now,
  }
  await page.route('http://127.0.0.1:8000/api/portfolio', (route) => route.fulfill({ json: [] }))
  await page.route('http://127.0.0.1:8000/api/sessions', (route) => route.fulfill({ json: [session] }))
  await page.route('http://127.0.0.1:8000/api/sessions/session-workflow', (route) => route.fulfill({ json: session }))
  await page.route('http://127.0.0.1:8000/api/projects/project-chat', (route) => route.fulfill({
    json: {
      id: 'project-chat',
      title: '霓虹雨夜',
      user_request: '生成一首雨夜电子纯音乐',
      preset: 'electronic_instrumental',
      status: 'completed',
      progress: 100,
      current_stage: 'completed',
      latest_run_id: 'run-chat',
    },
  }))
  await page.route('http://127.0.0.1:8000/api/projects/project-chat/runs/run-chat', (route) => route.fulfill({
    json: {
      id: 'run-chat',
      project_id: 'project-chat',
      status: 'completed',
      progress: 100,
      current_stage: 'completed',
      state: {
        workflow: 'electronic_instrumental',
        generated_tracks: [{
          title: '霓虹雨夜',
          source_url: 'https://audio.test/neon.mp3',
          local_path: '/tmp/neon.mp3',
          audio_url: '/works/neon.mp3',
          download_url: '/works/neon.mp3',
          cover_url: 'http://127.0.0.1:5173/icons.png',
          style: 'Ambient Electronic',
          duration_seconds: 180,
        }],
        generated_audio_analysis: [{
          track_title: '霓虹雨夜',
          waveform_url: 'http://127.0.0.1:5173/icons.png',
          inspection: { duration_seconds: 180, codec_name: 'mp3', sample_rate: 44100 },
        }],
      },
    },
  }))

  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('/?session=session-workflow')
  await expect(page.getByLabel('霓虹雨夜 工作流')).toBeVisible()
  await expect(page.getByText('电子器乐')).toBeVisible()
  await expect(page.getByText('已完成')).toBeVisible()
  await expect(page.locator('.chat-track audio')).toHaveAttribute('src', /works\/neon\.mp3/)
  await expect(page.getByTitle('下载音乐')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(1440)
  await page.screenshot({ path: '/tmp/nanguos-chat-workflow.png', fullPage: true })

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByLabel('霓虹雨夜 工作流')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  await page.screenshot({ path: '/tmp/nanguos-chat-workflow-mobile.png', fullPage: true })
})

test('sends a chat prompt with a persisted audio attachment', async ({ page }) => {
  const now = '2026-07-16T12:00:00Z'
  let session = {
    id: 'session-upload',
    title: '参考音频创作',
    messages: [] as Array<Record<string, unknown>>,
    assets: [] as Array<Record<string, unknown>>,
    created_at: now,
    updated_at: now,
  }
  let sentAssetIds: string[] = []
  await page.route('http://127.0.0.1:8000/api/portfolio', (route) => route.fulfill({ json: [] }))
  await page.route('http://127.0.0.1:8000/api/sessions', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({ status: 201, json: session })
      return
    }
    await route.fulfill({ json: session.messages.length ? [session] : [] })
  })
  await page.route('http://127.0.0.1:8000/api/sessions/session-upload/assets', async (route) => {
    const attachment = {
      id: 'audio-1',
      filename: 'reference-demo.wav',
      path: 'assets/audio-1.wav',
      content_type: 'audio/wav',
      size: 12,
    }
    session = { ...session, assets: [attachment] }
    await route.fulfill({ status: 201, json: attachment })
  })
  await page.route('http://127.0.0.1:8000/api/sessions/session-upload/messages', async (route) => {
    const payload = route.request().postDataJSON() as { content: string; asset_ids: string[] }
    sentAssetIds = payload.asset_ids
    session = {
      ...session,
      messages: [
        {
          id: 'user-1',
          role: 'user',
          content: payload.content,
          audio_attachments: session.assets,
          created_at: now,
        },
        { id: 'assistant-1', role: 'assistant', content: '已收到参考音频。', created_at: now },
      ],
    }
    await route.fulfill({
      json: {
        session,
        message: session.messages[1],
        action: 'chat_only',
      },
    })
  })

  await page.goto('/')
  await page.locator('.chat-file-input').setInputFiles({
    name: 'reference-demo.wav',
    mimeType: 'audio/wav',
    buffer: Buffer.from('demo'),
  })
  await expect(page.getByText('reference-demo.wav')).toBeVisible()
  await page.getByPlaceholder(/以后默认给我做纯音乐/).fill('参考这个 demo 创作一首电子纯音乐')
  await page.getByTitle('发送').click()

  await expect(page.getByText('已收到参考音频。')).toBeVisible()
  await expect(page.locator('.chat-audio-attachment').getByText('reference-demo.wav')).toBeVisible()
  expect(sentAssetIds).toEqual(['audio-1'])
  await page.screenshot({ path: '/tmp/nanguos-chat-audio.png', fullPage: true })
})

test('renders the portfolio as a cover-led music library', async ({ page }) => {
  await page.route('http://127.0.0.1:8000/api/portfolio', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify([
        {
          project_id: 'completed-project',
          title: '雨夜电子组曲',
          user_request: '雨夜中的氛围电子纯音乐',
          preset: 'electronic_instrumental',
          status: 'completed',
          progress: 100,
          current_stage: 'completed',
          latest_run_id: 'run-1',
          updated_at: '2026-07-16T10:00:00Z',
          tracks: [
            {
              title: '霓虹雨幕',
              audio_url: '/works/neon-rain.mp3',
              download_url: '/works/neon-rain.mp3',
              cover_url: 'http://127.0.0.1:5173/icons.png',
              duration_seconds: 187,
              style: 'Ambient Electronic · Cinematic',
            },
            {
              title: '凌晨列车',
              audio_url: '/works/midnight-train.mp3',
              download_url: '/works/midnight-train.mp3',
              cover_url: 'http://127.0.0.1:5173/icons.png',
              duration_seconds: 214,
              style: 'Downtempo · Synthwave',
            },
          ],
        },
        {
          project_id: 'running-project',
          title: '远行之歌',
          user_request: '公路电影配乐',
          preset: 'soundtrack_score',
          status: 'running',
          progress: 75,
          current_stage: 'demo_audio',
          latest_run_id: 'run-2',
          updated_at: '2026-07-16T11:00:00Z',
          tracks: [],
        },
      ]),
    })
  })
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('/')
  await page.getByRole('button', { name: '作品集' }).click()

  await expect(page.getByRole('heading', { name: '作品集', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: '霓虹雨幕' })).toBeVisible()
  await expect(page.getByText('3:07').first()).toBeVisible()
  await expect(page.getByText('75%')).toBeVisible()
  await expect(page.locator('.library-track')).toHaveCount(2)
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(1440)
  await page.screenshot({ path: '/tmp/nanguos-portfolio.png', fullPage: true })

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByRole('heading', { name: '霓虹雨幕' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  await page.screenshot({ path: '/tmp/nanguos-portfolio-mobile.png', fullPage: true })
})
