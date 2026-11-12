// Placeholder until the tour writer lands the real screenplay data (see ../../../tour/script.md).
export interface Beat {
  id: string
  set: string
  caption: string
  hero: { form: 'parcel' | 'postit' | 'envelope' | 'slip' | 'recording' | 'none'; at: string }
  lines: { who: string; text: string }[]
  bulb?: 'normalization' | 'failopen' | 'fanout' | 'eventcommand' | 'retention' | 'workqueue' | 'idempotent'
  teaches: string
}

export const CAST: Record<string, { name: string; role: string; real: string; color: string; accent: string; height: number }> = {
  damian: { name: 'Damian', role: 'new hire', real: 'you', color: '#F97316', accent: '#FDE68A', height: 0.85 },
  manager: { name: 'The Floor Manager', role: 'in a hurry', real: 'the requester', color: '#1F3A5F', accent: '#FACC15', height: 1.25 },
}

export const TOUR: Beat[] = [
  {
    id: 'brief', set: 'entrance', caption: 'The entrance', hero: { form: 'parcel', at: 'entrance' },
    lines: [
      { who: 'manager', text: "Look, I know you're new here. But what better way to learn your way around the campus. Or something." },
      { who: 'manager', text: "I need you to deliver this message to the guys down in Voxxy. It's packaged up, so you'll take it through processing yourself." },
      { who: 'manager', text: "When the guys are done, take their result and bring it back here. I'll be waiting for you." },
      { who: 'damian', text: '…Right.' },
    ],
    teaches: 'A request starts as a parcel in your tool’s own packing.',
  },
  {
    id: 'dock', set: 'dock', caption: 'Receiving dock', hero: { form: 'postit', at: 'dock' },
    lines: [{ who: 'damian', text: 'The script for this tour is still being written. This is a placeholder stop.' }],
    bulb: 'normalization', teaches: 'Parcels in, post-its out.',
  },
  {
    id: 'belt', set: 'belt', caption: 'The belt', hero: { form: 'envelope', at: 'belt' },
    lines: [{ who: 'damian', text: 'Placeholder: the belt.' }],
    teaches: 'Height is age.',
  },
]
