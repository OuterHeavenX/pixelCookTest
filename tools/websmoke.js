/* The browser build's smoke test: boots index.html in a real browser, plays it
 * through every mode with real key presses, screenshots each one, and reports.
 *
 * Run it through tools/websmoke.py, which finds node, playwright and a
 * browser; this file is the harness, the way godot/scripts/Smoke.gd is the
 * harness the Godot runner drives.
 *
 * The rule this exists for: drive the game the way a player does. A suite that
 * calls the game's own functions proves the functions work and nothing about
 * the paths that reach them. Random encounters were dead in a shipped build
 * for a whole chapter because every test called startEncounter() directly and
 * none of them ever took a step.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const PAGE = process.env.RIVEN_PAGE;
const SHOTS = process.env.RIVEN_SHOTS;
const VIEW = (process.env.RIVEN_VIEW || '960x540').split('x').map(Number);
const DPR = Number(process.env.RIVEN_DPR || 1);
const TOUCH = process.env.RIVEN_TOUCH === '1';

let failures = [];
let checks = 0;
let shots = 0;
/* Module scope, not inside the run, so that when the harness falls over the
   handler can still say what the page threw. A broken game trips the harness
   long before it finishes, and the useful line is always the page's own
   exception rather than whatever the harness tripped over afterwards. */
const errs = [];
let lastSection = '(start)';

function say(line) { process.stdout.write(line + '\n'); }
function section(name) { lastSection = name; say(name); }
function expect(cond, label, extra) {
  checks++;
  if (cond) {
    say('  ok   ' + label + (extra ? '  <' + extra + '>' : ''));
  } else {
    failures.push(label);
    say('  FAIL ' + label + (extra ? '  <' + extra + '>' : ''));
  }
  return !!cond;
}

/* Playwright resolves its own browser by default. When the installed
 * playwright and the installed browsers are different builds - which is the
 * normal state of a machine that got them from different places - it looks for
 * a revision that is not there, so fall back to whatever chromium actually is. */
async function launch() {
  try {
    return await chromium.launch();
  } catch (err) {
    const root = process.env.PLAYWRIGHT_BROWSERS_PATH;
    if (!root || !fs.existsSync(root)) throw err;
    for (const dir of fs.readdirSync(root).sort().reverse()) {
      if (!dir.startsWith('chromium-')) continue;
      for (const rel of ['chrome-linux/chrome', 'chrome-mac/Chromium.app/Contents/MacOS/Chromium',
                         'chrome-win/chrome.exe']) {
        const exe = path.join(root, dir, rel);
        if (fs.existsSync(exe)) return await chromium.launch({ executablePath: exe });
      }
    }
    throw err;
  }
}

(async () => {
  const browser = await launch();
  const ctx = await browser.newContext({
    viewport: { width: VIEW[0], height: VIEW[1] },
    deviceScaleFactor: DPR,
    isMobile: TOUCH,
    hasTouch: TOUCH,
    userAgent: TOUCH ? 'Mozilla/5.0 (Linux; Android 14) Mobile Safari/537.36' : undefined,
  });
  const p = await ctx.newPage();

  /* Any uncaught exception or console error fails the run outright. The game
   * carries on drawing after one - the last frame stays on screen - so a
   * screenshot of a broken build looks exactly like a screenshot of a working
   * one, and only this notices. */
  p.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push('CONSOLE: ' + m.text()); });

  await p.goto('file://' + PAGE);
  await p.waitForFunction(() => typeof G !== 'undefined' && G.mode, null, { timeout: 20000 });
  await p.waitForTimeout(400);

  // --- helpers ------------------------------------------------------------
  const ev = (fn, arg) => p.evaluate(fn, arg);
  const mode = () => ev(() => G.mode);
  const shot = async name => {
    if (!SHOTS) return;
    await p.locator('#screen').screenshot({ path: path.join(SHOTS, 'web_' + name + '.png') });
    shots++;
  };
  const press = async (key, ms) => { await p.keyboard.press(key); await p.waitForTimeout(ms || 130); };
  const until = async (fn, tries) => {
    for (let i = 0; i < (tries || 60); i++) {
      if (await ev(fn)) return true;
      await p.waitForTimeout(60);
    }
    return await ev(fn);
  };
  const msgLine = () => ev(() => Field.msg ? Field.msg.lines[Field.msg.page] : null);
  /* Press through a message the way a player reads it. Stops when a choice is
   * up and waiting, because that wants a decision rather than another press. */
  const readMsg = async (max = 40) => {
    const waiting = () => ev(() => !!Field.msg && !(Field.msg.choice &&
      Field.msg.page === Field.msg.lines.length - 1 &&
      Field.msg.chars >= Field.msg.lines[Field.msg.page].length));
    let n = 0;
    while (n < max && await waiting()) { await press('KeyZ', 110); n++; }
    return n;
  };
  const pickChoice = async (index = 0) => {
    for (let i = 0; i < 6 && await ev(() => !!Field.msg && !!Field.msg.choice); i++) {
      if (index > 0 && await ev(() => Field.msg.chars >= Field.msg.lines[Field.msg.page].length)) {
        for (let k = 0; k < index; k++) await press('ArrowDown', 100);
        index = 0;
      }
      await press('KeyZ', 150);
    }
    await readMsg();
  };
  const go = async (map, x, y) => {
    await ev(([m, mx, my]) => { enterMap(m, mx, my, 'down'); G.stepsToEncounter = 9999; },
      [map, x, y]);
    await p.waitForTimeout(320);
  };
  /* Walk up to somebody and talk. Calling recruit() directly is not the same
   * test: it passed for a while against a build where the conversation ended
   * without ever running what it was for, so nobody joined. */
  const talkTo = async who => {
    const placed = await ev(v => {
      const n = Field.npcs.find(q => q.name === v);
      if (!n) return false;
      n.cool = 999;                       // wanderers do not wander mid-test
      for (const [dx, dy, dir] of [[0, 1, 'up'], [0, -1, 'down'], [1, 0, 'left'], [-1, 0, 'right']]) {
        if (solidAt(n.tx + dx, n.ty + dy)) continue;
        G.px = n.tx + dx; G.py = n.ty + dy; G.dir = dir;
        return true;
      }
      return false;
    }, who);
    if (!placed) return false;
    await p.waitForTimeout(160);
    await ev(() => interact());
    await p.waitForTimeout(200);
    if (!await ev(() => !!Field.msg)) return false;
    await readMsg();
    return true;
  };
  const winFight = async () => {
    await until(() => G.mode === 'battle' && Battle.phase !== 'intro', 80);
    await ev(() => Battle.enemies.forEach(e => { e.hp = 0; e.alive = false; }));
    await until(() => Battle.phase === 'result', 80);
    for (let i = 0; i < 20 && await ev(() => G.mode === 'battle'); i++) await press('KeyZ', 160);
    await p.waitForTimeout(600);
  };

  // --- title --------------------------------------------------------------
  section('title');
  expect(await mode() === 'title', 'boots to the title screen', await mode());
  expect(await ev(() => VW >= 320 && VH >= 180), 'with a view at least as big as the game',
    await ev(() => VW + 'x' + VH));
  await shot('title');

  // --- field --------------------------------------------------------------
  section('field');
  await press('KeyZ', 900);
  expect(await mode() === 'field', 'New Game reaches the field');
  expect(await ev(() => G.party.length) === 3, 'three characters in the party');
  expect(await ev(() => G.mapId) === 'town', 'starts in town');
  await shot('field');

  /* On foot. Nothing else in the suite takes a step, and a stray line in the
   * encounter path once made every step throw. */
  await go('wild', 28, 22);
  await ev(() => { G.stepsToEncounter = 2; });
  let walked = false;
  for (let i = 0; i < 40 && !walked; i++) {
    await p.keyboard.down(i % 2 ? 'ArrowRight' : 'ArrowLeft');
    await p.waitForTimeout(120);
    await p.keyboard.up(i % 2 ? 'ArrowRight' : 'ArrowLeft');
    await p.waitForTimeout(50);
    walked = await ev(() => G.mode === 'battle');
  }
  expect(walked, 'walking into the grass starts a fight',
    await ev(() => Battle.enemies ? Battle.enemies.map(e => e.name).join(', ') : '-'));
  await shot('encounter');
  await winFight();
  expect(await mode() === 'field', 'and winning gives the field back');

  // --- equipment ----------------------------------------------------------
  section('equipment');
  await go('town', 20, 24);
  const atk = await ev(() => {
    const h = findHero('aldric');
    return [h.atk, GEAR[h.gear.weapon].stats.atk];
  });
  expect(atk[0] > atk[1], "Aldric's sword is counted in his attack", 'atk ' + atk[0]);
  expect(await ev(() => !!findHero('aldric').gear.weapon), 'Aldric starts armed');
  /* On Lyra, who starts with nothing on. Aldric is already wearing a leather
     vest, so putting a second one on him proves only that the number did not
     move. */
  const vest = await ev(() => {
    const h = findHero('lyra');
    const before = h.def;
    takeGear('silk_robe');
    equipGear(h, 'armour', 'silk_robe');
    return [before, h.def];
  });
  expect(vest[1] > vest[0], 'armour raises DEF on somebody who had none',
    vest[0] + ' -> ' + vest[1]);
  const charm = await ev(() => {
    const h = findHero('aldric');
    const before = h.hp;
    takeGear('guard_charm');
    equipGear(h, 'trinket', 'guard_charm');
    return [before, h.hp];
  });
  expect(charm[1] > charm[0], 'a +HP charm moves current HP too',
    charm[0] + ' -> ' + charm[1]);

  // --- menu ---------------------------------------------------------------
  section('menu');
  await press('KeyC', 400);
  expect(await mode() === 'menu', 'the menu opens');
  await shot('menu');
  await ev(() => { Menu.state = 'equip'; Menu.who = 0; });
  await p.waitForTimeout(250);
  await shot('menu_equip');
  await ev(() => { Menu.state = 'status'; });
  await p.waitForTimeout(250);
  await shot('menu_status');
  await press('KeyX', 250);
  await press('KeyX', 350);
  expect(await mode() === 'field', 'and closes back to the field', await mode());

  // --- shop ---------------------------------------------------------------
  section('shop');
  await ev(() => { G.gil = 5000; openShop('amber'); });
  await p.waitForTimeout(350);
  expect(await mode() === 'shop', 'the shop opens');
  const shelf = await ev(() => { Shop.tab = 1; return shopStock().length; });
  expect(shelf === (await ev(() => GEAR_STOCK.amber.length)),
    'the armoury lists every piece on its shelf (' + shelf + ')');
  await shot('shop');
  const bought = await ev(() => {
    const before = G.gil, it = shopStock()[0];
    Shop.index = 0;
    buyStock(0);
    // `gear` is a flag on the row, not the id; the id is the id either way.
    const held = (G.gear[it.id] || 0) +
      bagList().filter(b => b.id === it.id).reduce((n, b) => n + b.n, 0);
    return [before, G.gil, it.id, held];
  });
  expect(bought[1] < bought[0], 'buying costs gil', bought[0] + ' -> ' + bought[1]);
  expect(bought[3] > 0, 'and the piece lands in the pack', bought[2]);
  await ev(() => { G.mode = 'field'; });
  await p.waitForTimeout(200);
  expect(await mode() === 'field', 'the shop closes');

  // --- battle -------------------------------------------------------------
  section('battle');
  await ev(() => { G.party.forEach(h => { for (let i = 0; i < 6; i++) grantExp(h, 700); }); });
  await ev(() => startEncounter(['goblin', 'goblin', 'wolf'], ''));
  expect(await until(() => G.mode === 'battle', 80), 'an encounter starts');
  expect(await until(() => Battle.phase === 'command' && Battle.actor, 200),
    "a character's turn comes up");
  await shot('battle');
  const cmds = await ev(() => commandsFor(Battle.actor).length);
  expect(cmds >= 4, 'the command window has its buttons (' + cmds + ')');
  const spells = await ev(() => {
    const mage = G.party.find(h => h.maxmp > 0);
    Battle.actor = mage; Battle.sub = 'magic';
    return subList(mage).length;
  });
  expect(spells > 0, 'the spell list fills (' + spells + ')');
  await shot('battle_magic');
  await ev(() => { Battle.sub = null; Battle.phase = 'target'; Battle.targetSide = 'enemy'; });
  await p.waitForTimeout(250);
  expect(await ev(() => Battle.phase) === 'target', 'Fight asks for a target');
  await shot('battle_target');
  const hp = await ev(() => {
    const e = Battle.enemies[0], before = e.hp;
    Battle.phase = 'active';
    applyDamage(e, physDamage(G.party[0], e, 1).dmg, false);
    return [before, e.hp];
  });
  expect(hp[1] < hp[0], 'an attack takes hit points off', hp[0] + ' -> ' + hp[1]);
  const xpBefore = await ev(() => ({
    total: Battle.enemies.reduce((t, e) => t + e.exp, 0),
    heroes: G.party.map(h => [h.exp, h.lv, h.alive]),
  }));
  await winFight();
  expect(await mode() === 'field', 'and the fight ends');
  const after = await ev(() => G.party.map(h => [h.exp, h.lv]));
  expect(after.every((a, i) => !xpBefore.heroes[i][2] || a[1] > xpBefore.heroes[i][1]
    || a[0] === xpBefore.heroes[i][0] + xpBefore.total),
    'every survivor banks the EXP the card shows',
    JSON.stringify({ total: xpBefore.total, before: xpBefore.heroes, after }));

  // --- the barrow ---------------------------------------------------------
  section('barrow');
  await go('barrow1', 20, 27);
  expect(await ev(() => G.mapId) === 'barrow1', 'the barrow loads');
  /* Aldric's moment: the re-cut sign, and whether the town gets word. */
  expect(await ev(() => !!(Field.msg && Field.msg.choice)), 'the barrow mouth asks whether to send word',
    await msgLine());
  await pickChoice(0);
  await readMsg();
  expect(await ev(() => !!G.flags.aldricWarned), 'and the runner goes back to Rivenbrook');
  expect(await ev(() => Field.map.encounters) === 'barrow',
    "it draws from the barrow's own encounter table");
  expect(await ev(() => Audio_.track) === 'barrow', 'and plays the barrow theme',
    await ev(() => Audio_.track));
  expect(await ev(() => solidAt(20, 13)), 'the gate is shut without the key');
  await ev(() => { G.px = 20; G.py = 14; G.dir = 'up'; interact(); });
  await p.waitForTimeout(220);
  expect(await ev(() => !!Field.msg), 'and says something when you try it', await msgLine());
  await readMsg();
  await ev(() => { G.flags.barrowKey = true; });
  expect(await ev(() => !solidAt(20, 13)), 'the key opens it');
  await shot('barrow');
  await go('barrow2', 18, 25);
  expect(await ev(() => G.mapId) === 'barrow2', 'the lower floor loads');
  /* Lyra's moment: a minute with the letters before anyone breaks them. */
  expect(await ev(() => Field.msg && Field.msg.speaker === 'Lyra' && !!Field.msg.choice),
    'Lyra asks for a minute with the letters', await msgLine());
  await pickChoice(0);
  await readMsg();
  expect(await ev(() => !!G.flags.lyraRead), 'and reads the name cut into them');
  expect(await ev(() => !!Field.npcs.find(n => n.boss === 'chieftain')),
    'the chieftain waits at the bottom');

  // --- the ending ---------------------------------------------------------
  section('ending');
  await ev(() => { G.px = 18; G.py = 7; G.dir = 'up'; interact(); });
  await p.waitForTimeout(250);
  expect(await ev(() => !!Field.msg), 'the ward in the floor can be read', await msgLine());
  await readMsg();
  await ev(() => { G.px = 18; G.py = 7; onStepComplete(); });
  await p.waitForTimeout(400);
  expect(await ev(() => Field.msg && Field.msg.speaker) === 'Ogre Chieftain',
    'stepping up to him stands him off the bier');
  await pickChoice(0);
  expect(await until(() => G.mode === 'battle', 80), 'and the chieftain fights');
  expect(await ev(() => Battle.banner), 'his banner names him', await ev(() => Battle.banner));
  await shot('boss');
  await winFight();
  expect(await ev(() => !!G.flags.sealBroken), 'his death breaks the ward');
  expect(await until(() => G.mode === 'ending', 60), 'the chapter closes');
  expect(await ev(() => Ending.which) === 'one', "on chapter one's ending");
  expect(await ev(() => G.mapId) === 'town', 'and leaves the party in Rivenbrook');
  expect(await ev(() => hasSave()), 'with the journal already written',
    await ev(() => saveProblem() || 'no problem'));
  await ev(() => { Ending.chars = 9999; });
  await p.waitForTimeout(220);
  await shot('ending');
  for (let i = 0; i < 12 && await ev(() => Ending.phase === 'beats'); i++) {
    await ev(() => { Ending.chars = 9999; });
    await press('KeyZ', 200);
  }
  expect(await ev(() => Ending.phase) !== 'beats', 'the beats give way to the card',
    await ev(() => Ending.phase));
  expect(await ev(() => endingBeats().some(b => b.lines.join(' ').indexOf('VAIL') >= 0)),
    'and the ending remembers what Lyra read');
  expect(await ev(() => endingBeats().some(b => b.lines.join(' ').indexOf('Every lamp on the wall') >= 0)),
    'and that the wall was lit for your return');
  await shot('ending_card');

  // --- afterwards ---------------------------------------------------------
  section('aftermath');
  /* The credits leave the game in the ending; a player comes back through
   * Continue, which is also the only thing that puts the field back in charge
   * of its own input. */
  await ev(() => { Ending.phase = 'hook'; });
  await p.waitForTimeout(150);
  await ev(() => { G.mode = 'title'; Title.index = 1; });
  await press('KeyZ', 900);
  expect(await mode() === 'field', 'Continue picks the game back up in the field',
    await mode());
  /* Mira's moment fires the moment you are back in charge in town: Tam,
   * shivering, and whether the party stays the night. */
  expect(await ev(() => Field.msg && Field.msg.speaker === 'Mira' && !!Field.msg.choice),
    'Mira asks to sit with the boy', await msgLine());
  await pickChoice(0);
  await readMsg();
  expect(await ev(() => !!G.flags.miraTended), 'and stays the night');
  await go('town', 20, 24);
  expect(await ev(() => !!Field.npcs.find(n => n.name === 'Elder Halvard' && npcStage(n))),
    'the town has something new to say');
  expect(await ev(() => Field.npcs.find(n => n.name === 'Tam').wander === false),
    'and Tam has stopped wandering');
  expect(await ev(() => pictureVariant('town')) === 'cold', 'and the town wears its frost');
  const sign = await ev(() => { G.px = 46; G.py = 38; return !!SIGN_AFTER.wild; });
  expect(sign, 'and the shrine sign reads differently');

  // --- chapter two --------------------------------------------------------
  section('chapter two');
  await go('shore', 3, 14);
  expect(await ev(() => G.mapId) === 'shore', 'the mere road loads');
  expect(await ev(() => Field.map.encounters) === 'shore', 'with its own encounter table');
  const cold = await ev(() => pickEncounter().map(i => ENEMIES[i].name));
  expect(cold.length > 0, 'that names real cold-country monsters', cold.join(', '));
  await shot('shore');
  await go('hollow', 21, 31);
  expect(await ev(() => G.mapId) === 'hollow', 'Hollowmere loads');
  await shot('hollow');
  expect(await talkTo('Bram'), 'you can walk up to Bram and talk');
  expect(await talkTo('Sera'), 'and to Sera');
  expect(await ev(() => inRoster('bram') && inRoster('sera')),
    'and asking is what makes them join');
  expect(await ev(() => G.bench.length) === 1, 'the fifth waits on the bench');
  expect(await ev(() => !Field.npcs.find(n => n.name === 'Bram')),
    'and they stop standing in the street');
  const hollowShelf = await ev(() => { openShop('hollow'); Shop.tab = 1; return shopStock().length; });
  expect(hollowShelf === await ev(() => GEAR_STOCK.hollow.length),
    'the armourer stocks cold-country work (' + hollowShelf + ')');
  await ev(() => { G.mode = 'field'; });

  // Bram's goodbye, then Sera in four movements.
  await go('shore', 45, 14);
  expect(await ev(() => !!Field.msg), 'the road has something to say about it', await msgLine());
  await shot('bram');
  const read = await readMsg();
  expect(read < 40, 'the scene reads to the end');
  expect(await ev(() => !inRoster('bram')), 'Bram stays behind');
  expect(await ev(() => Object.keys(G.gear).length) > 0, 'and leaves his kit with you');

  await go('shore', 45, 14);
  expect(await ev(() => Field.msg && Field.msg.speaker) === 'Sera',
    'the road gives her the first word', await msgLine());
  await readMsg();
  expect(await ev(() => !!G.flags.seraDusk), 'and it stays said');
  await go('hollow', 21, 31);
  expect(await ev(() => !!Field.msg), 'she gives you something in town', await msgLine());
  await readMsg();
  expect(await ev(() => (G.gear['lamp_key'] || 0) > 0), 'and the lamp key lands in the pack');
  expect(await ev(() => canWear(findHero('aldric'), GEAR.lamp_key) &&
    !canWear(findHero('sera'), GEAR.lamp_key)), "and it is his to wear, nobody else's");
  await go('shore', 45, 14);
  await readMsg();
  expect(await ev(() => !!(Field.msg && Field.msg.choice)), 'the road asks you something',
    await ev(() => Field.msg && Field.msg.choice ? Field.msg.choice.options.join(' / ') : '-'));
  await shot('sera');
  await pickChoice(0);
  expect(await ev(() => !!G.flags.seraClose), 'sitting with her is an answer');
  await go('hollow', 21, 31);
  await readMsg();
  expect(await ev(() => !!G.flags.seraKeptTwice),
    'and she answers the question she would not answer');
  expect(await ev(() => !G.flags.seraKeptQuiet), 'and the other answer stays unsaid');

  // --- under the mere -----------------------------------------------------
  section('the mere');
  await go('hollow', 21, 31);
  await readMsg();
  expect(await ev(() => !!G.flags.mereOpened), "she opens the keepers' hatch");
  expect(await ev(() => !solidAt(20, 8)), 'and it is a way through now, not a wall');
  await go('mere1', 20, 25);
  expect(await ev(() => G.mapId) === 'mere1', "the keepers' road loads");
  expect(await ev(() => !!Field.msg), 'and she counts the lamps on it', await msgLine());
  await readMsg();
  await shot('mere');
  const deep = await ev(() => pickEncounter().map(i => ENEMIES[i].name));
  expect(deep.length > 0, 'with monsters of its own', deep.join(', '));
  await go('mere2', 18, 22);
  expect(await ev(() => G.mapId) === 'mere2', 'the cutting floor loads');
  await readMsg();
  expect(await ev(() => !!Field.npcs.find(n => n.name === 'Kestrel Vail')),
    'Kestrel is at the ward');
  expect(await ev(() => !!Field.npcs.find(n => n.boss === 'drowned')),
    'and the Warden is standing on it');
  expect(await talkTo('Kestrel Vail'), 'and she can be talked to');
  await shot('kestrel');
  await ev(() => { G.px = 18; G.py = 7; G.dir = 'up'; onStepComplete(); });
  await p.waitForTimeout(400);
  expect(await ev(() => Field.msg && Field.msg.speaker) === 'Drowned Warden',
    'stepping onto the letters stands it up');
  await shot('warden');
  await pickChoice(0);
  expect(await until(() => G.mode === 'battle', 80), 'the Warden fights');
  await winFight();
  expect(await ev(() => !!G.flags.wardenDown), 'and killing it quiets the ward');
  expect(await until(() => G.mode === 'ending', 60), 'the chapter closes');
  expect(await ev(() => Ending.which) === 'two', "on chapter two's ending, not chapter one's");
  expect(await ev(() => G.mapId) === 'hollow', 'and leaves you up in Hollowmere');
  await ev(() => { Ending.chars = 9999; });
  await p.waitForTimeout(250);
  await shot('end2');
  for (let i = 0; i < 14 && await ev(() => Ending.phase === 'beats'); i++) {
    await ev(() => { Ending.chars = 9999; });
    await press('KeyZ', 200);
  }
  expect(await ev(() => Ending.phase) !== 'beats', "chapter two's beats give way to its card");
  expect(await ev(() => ending().subtitle) === 'THE COLD BELOW', 'and it is the right card',
    await ev(() => ending().title + ' / ' + ending().subtitle));
  await shot('end2_card');

  // --- the journal --------------------------------------------------------
  section('save');
  await ev(() => { G.mode = 'field'; });
  expect(await ev(() => saveGame()), 'the journal saves');
  const before = await ev(() => [G.party.length, G.bench.length,
    JSON.stringify(G.party[1].gear)]);
  await ev(() => { G.party = []; G.bench = []; });
  expect(await ev(() => loadGame()), 'the journal loads');
  expect(await ev(() => G.party.length) === before[0], 'the party comes back');
  /* The bench is the half of the roster a save could quietly drop: nothing on
   * screen would look wrong until you opened the menu and found her gone. */
  expect(await ev(() => G.bench.length) === before[1], 'and so does the bench');
  expect(await ev(() => inRoster('sera')), 'with Sera still on it');
  expect(await ev(() => !inRoster('bram')), 'and Bram still up on the road');
  expect(await ev(() => JSON.stringify(G.party[1].gear)) === before[2],
    'equipment survives the round trip');
  /* The game writes its own save at the milestones, in a slot of its own. */
  expect(await ev(() => !!localStorage.getItem(AUTOSAVE_KEY)), 'the game has been autosaving');
  expect(await ev(() => JSON.parse(localStorage.getItem(SAVE_KEY)).version) === 2,
    'the journal carries a version');
  /* A save that cannot be trusted is refused with a reason, not loaded and
   * left to misbehave later. Both slots are broken so nothing sound is left. */
  await ev(() => { window.__kept = [localStorage.getItem(SAVE_KEY), localStorage.getItem(AUTOSAVE_KEY)]; });
  await ev(() => {
    localStorage.setItem(SAVE_KEY, JSON.stringify({ version: 2, party: [{ id: 'nobody', lv: 1, exp: 0, hp: 1, mp: 0 }], gil: 0, mapId: 'town', px: 1, py: 1 }));
    localStorage.setItem(AUTOSAVE_KEY, 'not json at all');
  });
  expect(await ev(() => !hasSave()), 'a broken journal is not offered');
  const why = await ev(() => saveProblem());
  expect(!!why && why.indexOf('nobody we know') >= 0, 'and the title says why', why);
  expect(await ev(() => !loadGame()), 'and cannot be loaded');
  await ev(() => {
    localStorage.setItem(SAVE_KEY, JSON.stringify({ party: [{ id: 'aldric', lv: 3, exp: 10, hp: 20, mp: 5 }], gil: 5, mapId: 'town', px: 2, py: 2, bag: { potion: 2, gone_item: 1 } }));
    localStorage.removeItem(AUTOSAVE_KEY);
  });
  expect(await ev(() => hasSave() && loadGame() && G.party.length === 1 && G.bag.potion === 2 && !G.bag.gone_item),
    'an old journal without a version still loads, minus what the game no longer has');
  await ev(() => { const k = window.__kept; localStorage.setItem(SAVE_KEY, k[0]); if (k[1]) localStorage.setItem(AUTOSAVE_KEY, k[1]); loadGame(); });

  // --- the screen ---------------------------------------------------------
  /* The view takes the shape of the window now, so a run at one shape proves
   * nothing about the others. These are the three that broke things: a wide
   * phone, an ordinary laptop, and a squarish screen. */
  section('the screen');
  for (const [label, w, h] of [['wide', 915, 412], ['laptop', 1440, 900], ['squarish', 800, 600]]) {
    await p.setViewportSize({ width: w, height: h });
    await p.waitForTimeout(260);
    const m = await ev(() => {
      const r = document.getElementById('screen').getBoundingClientRect();
      return { VW, VH, cw: Math.round(r.width), ch: Math.round(r.height),
               vw: window.innerWidth, vh: window.innerHeight };
    });
    const fillsW = m.cw / m.vw, fillsH = m.ch / m.vh;
    expect(m.VW >= 320 && m.VH >= 180 && m.VW <= 512 && m.VH <= 288,
      label + ': the view stays inside its bounds', m.VW + 'x' + m.VH);
    expect(fillsW > 0.9 && fillsH > 0.9, label + ': and fills the window',
      (fillsW * 100).toFixed(0) + '% x ' + (fillsH * 100).toFixed(0) + '%');
    expect(m.VW % 2 === 0 && m.VH % 2 === 0, label + ': on even numbers');
  }
  await p.setViewportSize({ width: VIEW[0], height: VIEW[1] });

  // --- verdict ------------------------------------------------------------
  if (errs.length) {
    say('');
    say('page errors:');
    for (const e of errs.slice(0, 20)) say('  ' + e);
  }
  say('');
  if (failures.length === 0 && errs.length === 0) {
    say('SMOKE OK  (' + checks + ' checks, ' + shots + ' screenshots)');
  } else {
    say('SMOKE FAILED (' + (failures.length + errs.length) + ')');
    for (const f of failures) say('  - ' + f);
    for (const e of errs.slice(0, 20)) say('  - ' + e);
  }
  await browser.close();
  process.exit(failures.length || errs.length ? 1 : 0);
})().catch(err => {
  // A throw here is the harness falling over, not the game failing a check,
  // and the two want telling apart.
  say('');
  if (errs.length) {
    say('the page threw first:');
    for (const e of errs.slice(0, 10)) say('  ' + e);
  }
  say('HARNESS STOPPED in "' + lastSection + '" after ' + checks + ' checks');
  say('  ' + (err && err.stack ? err.stack.split('\n')[0] : err));
  if (failures.length) {
    say('  failures before it:');
    for (const f of failures) say('    - ' + f);
  }
  process.exit(2);
});
