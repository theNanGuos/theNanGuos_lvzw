import { expect, test } from '@playwright/test'

test('renders the agent workspace on desktop', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/')

  await expect(page.getByRole('heading', { name: '音乐创作对话' })).toBeVisible()
  await expect(page.getByPlaceholder(/以后默认给我做纯音乐/)).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(1440)
  await page.screenshot({ path: '/tmp/nanguos-desktop.png', fullPage: true })
})

test('keeps controls readable on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')

  await expect(page.getByRole('heading', { name: '音乐创作对话' })).toBeVisible()
  await page.getByRole('button', { name: '创作台' }).click()
  await expect(page.getByRole('button', { name: '召集乐团开始创作' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  await page.screenshot({ path: '/tmp/nanguos-mobile.png', fullPage: true })
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
