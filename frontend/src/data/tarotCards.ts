export interface TarotCard {
  id: number
  name: string
  arcana: 'major' | 'minor'
  suit?: string
  upright: string
  reversed: string
  keywords: string[]
  symbol: string
  description: string
}

export const MAJOR_ARCANA: TarotCard[] = [
  {
    id: 0, name: 'The Fool', arcana: 'major', symbol: '🌟',
    upright: 'New beginnings, innocence, spontaneity, free spirit',
    reversed: 'Naivety, foolishness, recklessness, risk-taking',
    keywords: ['beginnings', 'innocence', 'adventure', 'potential'],
    description: 'The Fool represents the start of a journey — full of wonder and infinite possibility. You stand at the precipice, ready to leap into the unknown with trust in the universe.',
  },
  {
    id: 1, name: 'The Magician', arcana: 'major', symbol: '✨',
    upright: 'Manifestation, willpower, resourcefulness, inspired action',
    reversed: 'Manipulation, untapped talents, trickery',
    keywords: ['willpower', 'manifestation', 'skill', 'resourcefulness'],
    description: 'The Magician channels divine energy into the material world. All four elements are at your command. Your focused intention can manifest anything you desire.',
  },
  {
    id: 2, name: 'The High Priestess', arcana: 'major', symbol: '🌙',
    upright: 'Intuition, sacred knowledge, divine feminine, inner voice',
    reversed: 'Secrets, disconnected from intuition, withdrawal',
    keywords: ['intuition', 'mystery', 'subconscious', 'inner knowing'],
    description: 'The High Priestess sits at the veil between worlds, keeper of mysteries. She urges you to trust your deepest intuition and the wisdom that comes from within.',
  },
  {
    id: 3, name: 'The Empress', arcana: 'major', symbol: '🌿',
    upright: 'Femininity, beauty, nature, abundance, fertility',
    reversed: 'Creative block, dependence on others, smothering',
    keywords: ['abundance', 'nature', 'fertility', 'creativity'],
    description: 'The Empress embodies the fertile abundance of Mother Nature. Creation flows through you effortlessly. Nurture your dreams as you would a garden.',
  },
  {
    id: 4, name: 'The Emperor', arcana: 'major', symbol: '👑',
    upright: 'Authority, structure, control, fatherhood, stability',
    reversed: 'Tyranny, rigidity, coldness, domination',
    keywords: ['authority', 'structure', 'stability', 'leadership'],
    description: 'The Emperor brings order to chaos. His throne is built on wisdom and discipline. Structure and boundaries create the foundation upon which you can build your empire.',
  },
  {
    id: 5, name: 'The Hierophant', arcana: 'major', symbol: '🏛️',
    upright: 'Tradition, spiritual wisdom, institutions, conformity',
    reversed: 'Personal beliefs, freedom, challenging the status quo',
    keywords: ['tradition', 'wisdom', 'institution', 'guidance'],
    description: 'The Hierophant bridges the divine and earthly realms, offering spiritual guidance rooted in tradition. Seek wisdom from those who have walked this path before.',
  },
  {
    id: 6, name: 'The Lovers', arcana: 'major', symbol: '💫',
    upright: 'Love, harmony, relationships, values alignment, choices',
    reversed: 'Self-love, disharmony, imbalance, misalignment',
    keywords: ['love', 'choice', 'harmony', 'relationships'],
    description: 'The Lovers represent the sacred union of opposites and the choices that define us. Every meaningful decision is ultimately a declaration of what you value most.',
  },
  {
    id: 7, name: 'The Chariot', arcana: 'major', symbol: '⚡',
    upright: 'Control, willpower, success, determination, assertion',
    reversed: 'Lack of control, opposition, lack of direction',
    keywords: ['willpower', 'victory', 'determination', 'control'],
    description: 'The Chariot charges forward with fierce determination. Opposing forces have been harnessed and directed by sheer will. Your victory comes through discipline and focus.',
  },
  {
    id: 8, name: 'Strength', arcana: 'major', symbol: '🦁',
    upright: 'Inner strength, bravery, compassion, patience, control',
    reversed: 'Self-doubt, weakness, insecurity, cowardice',
    keywords: ['courage', 'patience', 'compassion', 'inner strength'],
    description: 'True Strength is the quiet power of compassion over force. The lion is tamed not by violence but by gentle, patient love — the greatest force in the universe.',
  },
  {
    id: 9, name: 'The Hermit', arcana: 'major', symbol: '🔦',
    upright: 'Soul searching, introspection, being alone, inner guidance',
    reversed: 'Isolation, loneliness, withdrawal, rejection',
    keywords: ['solitude', 'introspection', 'wisdom', 'guidance'],
    description: 'The Hermit retreats from the noise of the world to find the light within. In silence and solitude, the deepest truths are revealed. Turn your lantern inward.',
  },
  {
    id: 10, name: 'Wheel of Fortune', arcana: 'major', symbol: '🎡',
    upright: 'Good luck, karma, life cycles, destiny, turning point',
    reversed: 'Misfortune, lack of control, clinging to control',
    keywords: ['fate', 'cycles', 'destiny', 'luck'],
    description: 'The Wheel of Fortune turns ceaselessly — what rises must fall, what falls must rise. You are at a significant turning point. Trust in the perfect timing of the universe.',
  },
  {
    id: 11, name: 'Justice', arcana: 'major', symbol: '⚖️',
    upright: 'Justice, fairness, truth, cause and effect, law',
    reversed: 'Unfairness, dishonesty, injustice, self-deception',
    keywords: ['fairness', 'truth', 'cause and effect', 'balance'],
    description: 'Justice holds the scales of cosmic law. Every action creates a consequence that echoes through time. Walk your path with integrity and truth shall be your shield.',
  },
  {
    id: 12, name: 'The Hanged Man', arcana: 'major', symbol: '🙃',
    upright: 'Suspension, surrender, restriction, letting go, new perspective',
    reversed: 'Delays, indecision, stalling, resistance',
    keywords: ['pause', 'surrender', 'perspective', 'sacrifice'],
    description: 'The Hanged Man willingly suspends himself to gain a new perspective. What feels like stagnation is actually a sacred pause. Surrender reveals what striving cannot.',
  },
  {
    id: 13, name: 'Death', arcana: 'major', symbol: '🦋',
    upright: 'Endings, change, transformation, transition, letting go',
    reversed: 'Resistance to change, inability to move on, stagnation',
    keywords: ['transformation', 'endings', 'transition', 'change'],
    description: 'Death is not an ending but a profound transformation. What must fall away does so to make room for the new. Embrace the beautiful butterfly emerging from what was.',
  },
  {
    id: 14, name: 'Temperance', arcana: 'major', symbol: '🌊',
    upright: 'Balance, moderation, patience, purpose, meaning',
    reversed: 'Imbalance, excess, self-healing, realignment',
    keywords: ['balance', 'moderation', 'patience', 'harmony'],
    description: 'Temperance pours the waters of life between vessels — a sacred alchemy of balance. Through patient, moderate action, you are being refined into something greater.',
  },
  {
    id: 15, name: 'The Devil', arcana: 'major', symbol: '⛓️',
    upright: 'Shadow self, attachment, addiction, restriction, sexuality',
    reversed: 'Releasing limiting beliefs, exploring dark thoughts, detachment',
    keywords: ['bondage', 'shadow', 'attachment', 'materialism'],
    description: 'The Devil shows you the chains you have placed upon yourself. Most bonds are illusions — yet they feel very real. The first step to freedom is seeing the chains clearly.',
  },
  {
    id: 16, name: 'The Tower', arcana: 'major', symbol: '⚡',
    upright: 'Sudden change, upheaval, chaos, revelation, awakening',
    reversed: 'Personal transformation, fear of change, averting disaster',
    keywords: ['upheaval', 'revelation', 'chaos', 'awakening'],
    description: 'The Tower strikes with sudden, necessary lightning. What crumbles was built on false foundations. From these ruins, you will build something that can withstand eternity.',
  },
  {
    id: 17, name: 'The Star', arcana: 'major', symbol: '⭐',
    upright: 'Hope, faith, rejuvenation, spirituality, renewal',
    reversed: 'Faithlessness, despair, hopelessness, disconnection',
    keywords: ['hope', 'renewal', 'inspiration', 'faith'],
    description: 'The Star pours healing waters of hope upon a weary world. After the storm, she appears with her gentle light. You are guided, you are supported, you are never alone.',
  },
  {
    id: 18, name: 'The Moon', arcana: 'major', symbol: '🌙',
    upright: 'Illusion, fear, the subconscious, confusion, complexity',
    reversed: 'Release of fear, repressed emotion, inner confusion',
    keywords: ['illusion', 'dreams', 'subconscious', 'intuition'],
    description: 'The Moon illuminates the path through the shadowy realms of the unconscious. Not all is as it appears. Journey through the dreamscape with your intuition as your compass.',
  },
  {
    id: 19, name: 'The Sun', arcana: 'major', symbol: '☀️',
    upright: 'Positivity, fun, warmth, success, vitality',
    reversed: 'Sadness, depression, self-doubt, lack of enthusiasm',
    keywords: ['joy', 'success', 'vitality', 'clarity'],
    description: 'The Sun blazes with radiant joy and abundance. After the mysteries of the moon comes the illuminating clarity of day. Celebrate — you are radiant and full of life.',
  },
  {
    id: 20, name: 'Judgement', arcana: 'major', symbol: '🎺',
    upright: 'Judgement, rebirth, inner calling, absolution, reflection',
    reversed: 'Self-doubt, refusal of self-examination, self-loathing',
    keywords: ['awakening', 'reflection', 'absolution', 'rebirth'],
    description: 'The trumpet of Judgement calls you to rise, transformed. Review your life with compassionate honesty. This is the moment of resurrection — you are being called to your highest self.',
  },
  {
    id: 21, name: 'The World', arcana: 'major', symbol: '🌍',
    upright: 'Completion, integration, accomplishment, travel, wholeness',
    reversed: 'Incompletion, stagnation, seeking closure',
    keywords: ['completion', 'wholeness', 'accomplishment', 'integration'],
    description: 'The World dancer celebrates the completion of a great cycle. You have integrated all lessons and stand in your wholeness. This ending is also the seed of a magnificent new beginning.',
  },
]

export const ALL_CARDS = MAJOR_ARCANA
