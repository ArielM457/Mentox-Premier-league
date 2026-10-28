const TEXT = {
  es: {
    pass: (a, b) => b ? `Pase de ${a} para ${b}.` : `${a} juega el balón.`,
    goal: (a) => `¡Gol de ${a}!`, shot: (a) => `Remate de ${a}.`, saved: (a) => `Remate de ${a}, detenido por el portero.`, blocked: (a) => `Remate bloqueado de ${a}.`, offTarget: (a) => `Remate desviado de ${a}.`,
    tackle: (a) => `Entrada de ${a} para disputar el balón.`, possession: (a) => `${a} recupera la posesión.`, pressure: (a) => `${a} presiona al poseedor.`, recovery: (a) => `${a} recupera el balón.`, foul: (a) => `Falta cometida por ${a}.`, yellow: (a) => `Tarjeta amarilla para ${a}.`, red: (a) => `Tarjeta roja para ${a}.`, injury: (a) => `El partido se detiene para atender a ${a}.`, restart: (a) => `${a} reanuda el juego.`, unknown: (a) => `Acción de ${a}.`,
  },
  en: {
    pass: (a, b) => b ? `Pass from ${a} to ${b}.` : `${a} plays the ball.`,
    goal: (a) => `Goal by ${a}!`, shot: (a) => `Shot by ${a}.`, saved: (a) => `${a}'s shot is saved.`, blocked: (a) => `${a}'s shot is blocked.`, offTarget: (a) => `${a} shoots off target.`,
    tackle: (a) => `${a} challenges for the ball.`, possession: (a) => `${a} wins possession.`, pressure: (a) => `${a} presses the ball carrier.`, recovery: (a) => `${a} recovers the ball.`, foul: (a) => `Foul by ${a}.`, yellow: (a) => `Yellow card for ${a}.`, red: (a) => `Red card for ${a}.`, injury: (a) => `Play stops for ${a} to receive treatment.`, restart: (a) => `${a} restarts play.`, unknown: (a) => `Action by ${a}.`,
  },
  de: {
    pass: (a, b) => b ? `Pass von ${a} zu ${b}.` : `${a} spielt den Ball.`, goal: (a) => `Tor durch ${a}!`, shot: (a) => `Schuss von ${a}.`, saved: (a) => `Der Schuss von ${a} wird gehalten.`, blocked: (a) => `Der Schuss von ${a} wird geblockt.`, offTarget: (a) => `${a} schießt vorbei.`, tackle: (a) => `${a} geht in den Zweikampf.`, possession: (a) => `${a} gewinnt den Ball.`, pressure: (a) => `${a} setzt den Ballführer unter Druck.`, recovery: (a) => `${a} erobert den Ball.`, foul: (a) => `Foul von ${a}.`, yellow: (a) => `Gelbe Karte für ${a}.`, red: (a) => `Rote Karte für ${a}.`, injury: (a) => `Das Spiel wird für ${a} unterbrochen.`, restart: (a) => `${a} setzt das Spiel fort.`, unknown: (a) => `Aktion von ${a}.`,
  },
  fr: {
    pass: (a, b) => b ? `Passe de ${a} vers ${b}.` : `${a} joue le ballon.`, goal: (a) => `But de ${a} !`, shot: (a) => `Tir de ${a}.`, saved: (a) => `Le tir de ${a} est arrêté.`, blocked: (a) => `Le tir de ${a} est contré.`, offTarget: (a) => `${a} tire à côté.`, tackle: (a) => `${a} dispute le ballon.`, possession: (a) => `${a} récupère la possession.`, pressure: (a) => `${a} presse le porteur.`, recovery: (a) => `${a} récupère le ballon.`, foul: (a) => `Faute de ${a}.`, yellow: (a) => `Carton jaune pour ${a}.`, red: (a) => `Carton rouge pour ${a}.`, injury: (a) => `Le jeu s'arrête pour soigner ${a}.`, restart: (a) => `${a} relance le jeu.`, unknown: (a) => `Action de ${a}.`,
  },
  pt: {
    pass: (a, b) => b ? `Passe de ${a} para ${b}.` : `${a} joga a bola.`, goal: (a) => `Gol de ${a}!`, shot: (a) => `Finalização de ${a}.`, saved: (a) => `Finalização de ${a}, defendida pelo goleiro.`, blocked: (a) => `Finalização bloqueada de ${a}.`, offTarget: (a) => `${a} finaliza para fora.`, tackle: (a) => `${a} disputa a bola.`, possession: (a) => `${a} recupera a posse.`, pressure: (a) => `${a} pressiona o portador da bola.`, recovery: (a) => `${a} recupera a bola.`, foul: (a) => `Falta cometida por ${a}.`, yellow: (a) => `Cartão amarelo para ${a}.`, red: (a) => `Cartão vermelho para ${a}.`, injury: (a) => `O jogo para para atender ${a}.`, restart: (a) => `${a} reinicia o jogo.`, unknown: (a) => `Jogada de ${a}.`,
  },
  zh: {
    pass: (a, b) => b ? `${a}传球给${b}。` : `${a}处理球。`, goal: (a) => `${a}进球！`, shot: (a) => `${a}射门。`, saved: (a) => `${a}的射门被扑出。`, blocked: (a) => `${a}的射门被封堵。`, offTarget: (a) => `${a}射门偏出。`, tackle: (a) => `${a}争抢球权。`, possession: (a) => `${a}夺回控球权。`, pressure: (a) => `${a}向持球人施压。`, recovery: (a) => `${a}抢回球权。`, foul: (a) => `${a}犯规。`, yellow: (a) => `${a}获得黄牌。`, red: (a) => `${a}获得红牌。`, injury: (a) => `比赛暂停，${a}接受治疗。`, restart: (a) => `${a}重新开始比赛。`, unknown: (a) => `${a}完成一次动作。`,
  },
  hi: {
    pass: (a, b) => b ? `${a} से ${b} को पास।` : `${a} गेंद खेलते हैं।`, goal: (a) => `${a} का गोल!`, shot: (a) => `${a} का शॉट।`, saved: (a) => `${a} का शॉट बचा लिया गया।`, blocked: (a) => `${a} का शॉट ब्लॉक हुआ।`, offTarget: (a) => `${a} का शॉट बाहर गया।`, tackle: (a) => `${a} गेंद के लिए चुनौती देते हैं।`, possession: (a) => `${a} ने कब्जा हासिल किया।`, pressure: (a) => `${a} गेंद वाले खिलाड़ी पर दबाव डालते हैं।`, recovery: (a) => `${a} गेंद वापस जीतते हैं।`, foul: (a) => `${a} ने फाउल किया।`, yellow: (a) => `${a} को पीला कार्ड।`, red: (a) => `${a} को लाल कार्ड।`, injury: (a) => `${a} के इलाज के लिए खेल रुका।`, restart: (a) => `${a} खेल दोबारा शुरू करते हैं।`, unknown: (a) => `${a} की कार्रवाई।`,
  },
}

function nameOf(metadata, playerId, teamId) {
  const player = metadata.players.find((item) => item.player_id === playerId)
  if (player) return player.name
  if (metadata.home_team.team_id === teamId) return metadata.home_team.name
  if (metadata.away_team.team_id === teamId) return metadata.away_team.name
  return teamId || '—'
}

export function eventCommentary(event, metadata, language = 'es') {
  const text = TEXT[language] ?? TEXT.en
  const actor = nameOf(metadata, event.player_id, event.team_id)
  const receiver = event.receiver_player_id ? nameOf(metadata, event.receiver_player_id) : null
  if (event.type === 'pass') return text.pass(actor, receiver)
  if (event.type === 'shot') {
    if (event.outcome === 'goal') return text.goal(actor)
    if (event.outcome === 'saved') return text.saved(actor)
    if (event.outcome === 'blocked') return text.blocked(actor)
    if (event.outcome === 'off_target') return text.offTarget(actor)
    return text.shot(actor)
  }
  const type = { tackle: 'tackle', possession_change: 'possession', pressure: 'pressure', recovery: 'recovery', foul: 'foul', yellow_card: 'yellow', red_card: 'red', injury_stoppage: 'injury', restart: 'restart' }[event.type]
  return text[type ?? 'unknown'](actor)
}

export function matchMinute(clockMs) {
  return `${Math.max(0, Math.floor(clockMs / 60_000))}'`
}
