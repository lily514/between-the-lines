// The words on the story steps: a title and a paragraph per strand for the welcome, and per concept and level for
// First look and Level-up. Example prompts come from the fixtures' real questions; these hold a fallback each.
import type { Band } from '../api/client.ts'

export interface StepCopy {
	title: string
	body: string
	example: string
}

/** The welcome's step per strand, at Getting there. */
export const WELCOME_COPY: Record<string, StepCopy> = {
	game_flow: {
		title: 'When play stops',
		body: 'Ball out, a foul, an offside flag. You say what happens next.',
		example: 'The ball’s gone out. What happens now?'
	},
	possession: {
		title: 'Passes that slice through',
		body: 'Some passes skip a whole wall of defenders. You learn to spot them.',
		example: 'Did that pass get past the defenders?'
	},
	pressure: {
		title: 'Win it straight back',
		body: 'Lose the ball, then swarm before the other team can settle.',
		example: 'Did they win it back in time?'
	},
	chances: {
		title: 'Shots, and what comes of them',
		body: 'A shot is saved, blocked, wide or in. You say what came of it, and where it came from.',
		example: 'What came of that shot?'
	}
}

/** Which concept's scene stands for a strand on the welcome. */
export const SCENE_FOR_STRAND: Record<string, string> = {
	game_flow: 'restarts',
	possession: 'line_breaking_pass',
	pressure: 'counter_press',
	chances: 'shots_and_goals'
}

/** Each concept's step at each level: First look uses Getting there, Level-up the level reached. */
export const CONCEPT_COPY: Record<string, Record<Band, StepCopy>> = {
	restarts: {
		getting_there: {
			title: 'Who gets it back?',
			body: 'When the ball goes out, the team that didn’t touch it last gets it. Over the side, that’s a throw-in.',
			example: 'The ball’s gone out. What happens now?'
		},
		solid: {
			title: 'Read the restart',
			body: 'Last touch decides it. Off a defender over the goal line is a corner. Off an attacker, a goal kick.',
			example: 'It came off a defender and over the goal line. What happens now?'
		},
		sharp: {
			title: 'Spot the hidden touch',
			body: 'Match data can miss a block. One faint touch turns a goal kick into a corner.',
			example: 'The data says the cross went out. What does the referee give?'
		}
	},
	offside: {
		getting_there: {
			title: 'Don’t get in behind early',
			body: 'When the pass is played, an attacker can’t be nearer goal than the last defenders. Level is fine.',
			example: 'Was that offside?'
		},
		solid: {
			title: 'Find the line',
			body: 'Find the second-last defender. Nearer goal than them when the pass is played is offside. Level is onside.',
			example: '#9 got the pass. Was he offside?'
		},
		sharp: {
			title: 'Freeze it at the pass',
			body: 'Offside is judged the moment the pass is played. Where the attacker is when it arrives doesn’t count.',
			example: '#9 is about to get the pass. Will the flag go up?'
		}
	},
	fouls_and_cards: {
		getting_there: {
			title: 'Foul, then free kick',
			body: 'After a foul, the fouled team gets a free kick where it happened. In the fouling team’s own box, a penalty.',
			example: 'There has been a foul. What happens now?'
		},
		solid: {
			title: 'Where it happened',
			body: 'A foul gives a free kick where it happened. Inside the fouling team’s own box, it’s a penalty.',
			example: 'Foul by #5. What happens now?'
		},
		sharp: {
			title: 'Contact, not landing',
			body: 'The contact decides the restart, not where the player lands. And not every foul is a booking.',
			example: 'He went down in the box. Penalty or free kick?'
		}
	},
	line_breaking_pass: {
		getting_there: {
			title: 'Passes that slice through',
			body: 'Some passes skip a whole wall of defenders at once. That’s how teams get close to goal.',
			example: 'Did that pass get past the defenders?'
		},
		solid: {
			title: 'Count the lines',
			body: 'Count the lines it gets past and find the gap. The receiver waits in the space between the lines.',
			example: 'How many lines did that pass break: none, one or two?'
		},
		sharp: {
			title: 'Follow the threat',
			body: 'Every zone carries a threat value. Breaking lines into a better zone is what lifts it.',
			example: 'Which pass adds the most threat: A, B or C?'
		}
	},
	counter_press: {
		getting_there: {
			title: 'Win it straight back',
			body: 'Lose the ball, then hunt it straight back before the other team can spread out.',
			example: 'Did they win it back quickly?'
		},
		solid: {
			title: 'Time the press',
			body: 'A counter-press is a group effort: several players close in while the other team is still turning.',
			example: 'How long did they take to win it back?'
		},
		sharp: {
			title: 'Weigh the risk',
			body: 'Winning it high starts an attack near goal. If the press fails, it leaves space behind.',
			example: 'Where did they win it back: own half, middle third or near their goal?'
		}
	}
}

CONCEPT_COPY.tackles = {
	getting_there: {
		title: 'Who won it, and how',
		body: 'Teams get the ball back with a tackle, an interception, or by picking up a loose ball. You say which.',
		example: 'They have just taken the ball. How did they win it?'
	},
	solid: {
		title: 'Where they won it',
		body: 'Win it in the middle third or higher and the other team is still turning. You say which third it was.',
		example: 'Where on the pitch did they win it?'
	},
	sharp: {
		title: 'Why the place matters',
		body: 'A ball won high starts an attack with the defence out of shape; one won deep leaves the whole pitch ahead.',
		example: 'Why does where they took it matter?'
	}
}

CONCEPT_COPY.shots_and_goals = {
	getting_there: {
		title: 'What came of the shot',
		body: 'A shot is saved, blocked, off target or in. You say what came of it.',
		example: 'What came of that shot?'
	},
	solid: {
		title: 'Where it was from',
		body: 'The six-yard box, the penalty area or outside it: where a shot comes from says most about the chance.',
		example: 'Where was the shot from?'
	},
	sharp: {
		title: 'How the chance came',
		body: 'A pass, a cross or a dribble made the chance. You say how it came about, with the shot count beside it.',
		example: 'How did the chance come about?'
	}
}

CONCEPT_COPY.transitions = {
	getting_there: {
		title: 'The moment after winning it',
		body: 'Win the ball and both teams are out of shape for a moment. Some go straight for goal; some build slowly.',
		example: 'They have just won the ball. What did they do next?'
	},
	solid: {
		title: 'How fast to the box',
		body: 'A counter-attack reaches the box in seconds, before the defence is back. You say how long it took.',
		example: 'How long did they take to reach the box?'
	},
	sharp: {
		title: 'What made it a counter',
		body: 'Going for goal at once, while the defence is still out of shape, is what makes a counter-attack. Not speed alone.',
		example: 'What made that a counter-attack?'
	}
}

/** The level a band's scene and copy are keyed by, as the fixtures number them. */
export const LEVEL_OF: Record<Band, '1' | '2' | '3'> = { getting_there: '1', solid: '2', sharp: '3' }
