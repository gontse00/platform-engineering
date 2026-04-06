export type QuickAction = {
  label: string
  value: string
}

const locationActions: QuickAction[] = [
  { label: 'Johannesburg', value: 'I am in Johannesburg' },
  { label: 'Randburg', value: 'I am in Randburg' },
  { label: 'Sandton', value: 'I am in Sandton' },
  { label: 'Soweto', value: 'I am in Soweto' },
]

const dangerActions: QuickAction[] = [
  { label: 'Yes, I am in danger', value: 'Yes, I am in danger' },
  { label: 'No, I am safe right now', value: 'No, I am safe right now' },
]

const injuryActions: QuickAction[] = [
  { label: 'I am injured', value: 'I am injured' },
  { label: 'I am not injured', value: 'I am not injured' },
]

const contactActions: QuickAction[] = [
  { label: 'Text me', value: 'Text me' },
  { label: 'Call me', value: 'Call me' },
]

const needActions: QuickAction[] = [
  { label: 'I need shelter', value: 'I need shelter' },
  { label: 'I need medical help', value: 'I need medical help' },
  { label: 'I need legal help', value: 'I need legal help' },
  { label: 'I need someone to talk to', value: 'I need someone to talk to' },
]

const fallbackActions: QuickAction[] = [
  { label: 'I need shelter', value: 'I need shelter' },
  { label: 'I need medical help', value: 'I need medical help' },
  { label: 'I need legal help', value: 'I need legal help' },
  { label: 'I need someone to talk to', value: 'I need someone to talk to' },
]

export function getQuickActionsForField(field?: string | null): QuickAction[] {
  switch (field) {
    case 'location':
      return locationActions
    case 'immediate_danger':
      return dangerActions
    case 'injury_status':
      return injuryActions
    case 'safe_contact_method':
      return contactActions
    case 'primary_need':
      return needActions
    default:
      return fallbackActions
  }
}

export function getQuickActionHint(field?: string | null): string {
  switch (field) {
    case 'location':
      return 'Choose your area or type it manually.'
    case 'immediate_danger':
      return 'Let us know whether you are in immediate danger right now.'
    case 'injury_status':
      return 'Tell us whether you are injured.'
    case 'safe_contact_method':
      return 'Choose the safest way for someone to contact you.'
    case 'primary_need':
      return 'Choose the kind of support you need most right now.'
    default:
      return 'You can use a quick action or type your answer in your own words.'
  }
}

export function getInputPlaceholder(field?: string | null): string {
  switch (field) {
    case 'location':
      return 'Type your area, suburb, or city.'
    case 'immediate_danger':
      return 'Tell us if you are in immediate danger.'
    case 'injury_status':
      return 'Tell us whether you are injured.'
    case 'safe_contact_method':
      return 'Tell us whether text or phone is safer.'
    case 'primary_need':
      return 'Describe the main kind of help you need.'
    default:
      return 'Describe what happened, where you are, and what help you need.'
  }
}