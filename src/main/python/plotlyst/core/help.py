"""
Plotlyst
Copyright (C) 2021-2024  Zsolt Kovari

This file is part of Plotlyst.

Plotlyst is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Plotlyst is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
from dataclasses import dataclass
from typing import Dict, List

from plotlyst.core.template import Role, protagonist_role, antagonist_role, major_role, secondary_role, \
    tertiary_role, \
    love_interest_role, supporter_role, adversary_role, contagonist_role, guide_role, confidant_role, sidekick_role, \
    foil_role, henchmen_role, enneagram_field

# flake8: noqa
enneagram_help = {
    enneagram_field.selections[0].text: '''<html>Ethical type who wants to be good and right, and often seeks to improve the world.<ul>
    <li><b>Desire</b>: Being good, balanced, have integrity</li>
    <li><b>Fear</b>: Being incorrect, corrupt, evil</li>
    </ul>''',
    enneagram_field.selections[1].text: '''<html>Generous, attentive type who loves to help people and make their surrounding a better place.<ul>
    <li><b>Desire</b>: To be loved and appreciated
    <li><b>Fear</b>: Being unloved, unwanted
    </ul>''',
    enneagram_field.selections[2].text: '''<html>Success-oriented type who values their image and driven for achievements.<ul>
    <li><b>Desire</b>: Be valuable and worthwhile
    <li><b>Fear</b>: Being worthless
    </ul>''',
    enneagram_field.selections[3].text: '''<html>Creative, sensitive type who feels unique and authentic and seeks ways to express it.<ul>
    <li><b>Desire</b>: Express their individuality
    <li><b>Fear</b>: Having no identity or significance
    </ul>''',
    enneagram_field.selections[4].text: '''<html>Independent, perceptive type who seeks knowledge and often prefers privacy and time alone.<ul>
    <li><b>Desire</b>: Be competent
    <li><b>Fear</b>: Being useless, incompetent
    </ul>''',
    enneagram_field.selections[5].text: '''<html>Loyal, hard-working, cautious type who seeks safety and security.<ul>
    <li><b>Desire</b>: Have security and support
    <li><b>Fear</b>: Being vulnerable and unprepared
    </ul>''',
    enneagram_field.selections[6].text: '''<html>Spontaneous, enthusiastic type who seeks new experiences.<ul>
    <li><b>Desire</b>: Be stimulated, engaged, satisfied
    <li><b>Fear</b>: Being deprived
    </ul>''',
    enneagram_field.selections[7].text: '''<html>Dominating, confident type who seeks to be powerful and avoid relying on others.<ul>
    <li><b>Desire</b>: Be independent and in control
    <li><b>Fear</b>: Being vulnerable, controlled, harmed
    </ul>''',
    enneagram_field.selections[8].text: '''<html>Optimistic, adaptive type who seek to maintain peace and harmony.<ul>
    <li><b>Desire</b>: Internal peace, harmony
    <li><b>Fear</b>: Loss, separation
    </ul>'''

}

mbti_help = {'ISTJ': '''<html><h3>The Inspector</h3>
                Dependable and systematic types who enjoy working within clear systems and processes. Traditional, task-oriented and decisive.
             ''',
             'ISFJ': '''<html><h3>The Protector</h3>
             ISFJs are patient individuals who apply common sense and experience to solving problems for other people. They are responsible, loyal and traditional, enjoying serving the needs of others and providing practical help.
             ''',
             'ESTP': '''<html><h3>The Dynamo</h3>
             ESTPs motivate others by bringing energy into situations. They apply common sense and experience to problems, quickly analysing what is wrong and then fixing it, often in an inventive or resourceful way.
             ''',
             'ESFP': '''<html><h3>The Performer</h3>
             ESFP people tend to be adaptable, friendly, and talkative. They enjoy life and being around people. This personality type enjoys working with others and experiencing new situations.
             ''',
             'INFJ': '''<html><h3>The Counselor</h3>
             INFJs may come across as individualistic, private and perhaps mysterious to others, and may do their thinking in a vacuum, resulting in an unrealistic vision that is difficult to communicate.
             ''',
             'INTJ': '''<html><h3>The Mastermind</h3>
             INTJ people are often able to define a compelling, long-range vision, and can devise innovative solutions to complex problems.
             ''',
             'ENFP': '''<html><h3>The Champion</h3>
             Moving quickly from one project to another, ENFPs are willing to consider almost any possibility and often develop multiple solutions to a problem. Their energy is stimulated by new people and experiences.
             ''',
             'ENTP': '''<html><h3>The Visionary</h3>
             ENTPs solve problems creatively and are often innovative in their way of thinking, seeing connections and patterns within a system. They enjoy developing strategy and often spot and capitalise on new opportunities that present themselves.
             ''',
             'ISFP': '''<html><h3>The Composer</h3>
             ISFPs enjoy providing practical help or service to others, as well as bringing people together and facilitating and encouraging their cooperation.
             ''',
             'INFP': '''<html><h3>The Healer</h3>
             INFP people enjoy devising creative solutions to problems, making moral commitments to what they believe in. They enjoy helping others with their growth and inner development to reach their full potential.
             ''',
             'ESFJ': '''<html><h3>The Provider</h3>
             ESFJs tend to be sociable and outgoing, understanding what others need and expressing appreciation for their contributions. They collect the necessary facts to help them make a decision and enjoy setting up effective procedures.
             ''',
             'ENFJ': '''<html><h3>The Teacher</h3>
             ENFJs are able to get the most out of teams by working closely with them, and make decisions that respect and take into account the values of others. They tend to be adept at building consensus and inspiring others as leaders.
             ''',
             'ISTP': '''<html><h3>The Craftsperson</h3>
             ISTPs tend to enjoy learning and perfecting a craft through their patient application of skills. They can remain calm while managing a crisis, quickly deciding what needs to be done to solve the problem.
             ''',
             'INTP': '''<html><h3>The Architect</h3>
             INTP people think strategically and are able to build conceptual models to understand complex problems. They tend to adopt a detached and concise way of analysing the world, and often uncover new or innovative approaches.
             ''',
             'ESTJ': '''<html><h3>The Supervisor</h3>
             ESTJs drive themselves to reach their goal, organising people and resources in order to achieve it. They have an extensive network of contacts and are willing to make tough decisions when necessary. They tend to value competence highly.
             ''',
             'ENTJ': '''<html><h3>The Commander</h3>
             ENTJs see the big picture and think strategically about the future. They are able to efficiently organise people and resources in order to accomplish long-term goals, and tend to be comfortable with taking strong leadership over others.
             '''
             }

mbti_keywords = {'ISTJ': "Dependable, systematic, traditional, task-oriented, decisive",
                 'ISFJ': "Patient, responsible, loyal, traditional, service-oriented",
                 'ESTP': "Energetic, analytical, inventive, resourceful, motivating",
                 'ESFP': "Adaptable, friendly, talkative, social, enjoyable",
                 'INFJ': "Individualistic, private, mysterious, visionary, thoughtful",
                 'INTJ': "Visionary, innovative, strategic, problem-solver, long-range planner",
                 'ENFP': "Quick-thinking, possibility-driven, energetic, creative, adaptable",
                 'ENTP': "Creative, innovative, strategic thinker, pattern recognizer, opportunity-seeker",
                 'ISFP': "Practical, service-oriented, cooperative, facilitator, encouraging",
                 'INFP': "Creative, moral, helping, growth-oriented, inner development",
                 'ESFJ': "Sociable, outgoing, understanding, appreciative, procedural",
                 'ENFJ': "Team-oriented, consensus builder, inspirational leader, values-driven, effective decision-maker",
                 'ISTP': "Patient, skilled, crisis manager, problem-solver, calm",
                 'INTP': "Strategic thinker, conceptual builder, analytical, detached, innovative",
                 'ESTJ': "Goal-oriented, organized, decisive, networked, competent",
                 'ENTJ': "Strategic thinker, goal-oriented, efficient, organized, strong leadership"
                 }

work_style_help = {
    'Drive': "Ambitious and results-oriented, enjoying challenges and taking charge. They're competitive and persuasive, driven by a desire for control and power.",
    'Clarity': "Detail-oriented and quality-conscious. They prioritize structure, organization, and correctness in their work, approaching challenges with caution.",
    'Support': "Harmony, structure, and organization. They are patient, accepting, and enjoy working behind the scenes as part of a team, contributing to the overall success in a supportive role.",
    'Influence': "Sociable types who excel in building relationships, networking, and persuading others, thriving in social situations and teamwork.",
}

love_style_help = {
    'Activity': "Individuals thrive when their partner shows interest in their hobbies and activities, emphasizing genuine engagement and connection beyond mere presence.",
    'Appreciation': "Individuals feel loved through words of praise and acknowledgment of their personal qualities and achievements, valuing verbal expressions of gratitude from their partner",
    'Emotional': "Individuals feel loved through emotional connection and support, receiving care and understanding during vulnerable times.",
    'Financial': "Individuals feel loved when their partner uses financial resources to bring them joy and delight, extending beyond material gifts to acts of generosity and thoughtfulness.",
    'Intellectual': "Individuals value mental connection and intelligent discourse, where feeling loved involves respect for one's intellect and engaging in thoughtful discussions.",
    'Physical': "Individuals feel loved through physical touch and intimacy, encompassing a range of tactile expressions beyond sexual acts.",
    'Practical': "Individuals feel loved when their partners provide practical assistance and support in daily tasks, with gestures that go beyond routine chores to show care and consideration.",
}

plot_value_help = """<html>When a storyline is linked to a scene, these values can be <b style=color:#52b788;>positively</b> or 
<b style=color:#9d0208;>negatively</b> charged, showcasing the storyline's advancement or setback.
<br>The changes can be also visualized in the analysis panel, depicting the story's arc.
</html>"""

scene_disaster_outcome_help = """<html><head/><body><p>Scene ends with a <span style=" font-weight:600; color:#f4442e;">disaster</span>,
 so the character's goal remains unresolved</p></body></html>"""

scene_trade_off_outcome_help = """<html><head/><body><p>Scene ends with a bittersweet <span style=" font-weight:600; color:#832161;">trade-off</span>,
 so the character's goal is achieved but not without a price</p></body></html>"""

scene_resolution_outcome_help = """<html><head/><body><p>Scene ends with a <span style=" font-weight:600; color:#6ba368;">resolution</span>,
 so the character's goal is achieved</p></body></html>"""

scene_motion_outcome_help = """<html><head/><body><p>Scene sets the story in motion without delivering any imminent disaster or resolution outcome</p></body></html>"""

mid_revision_scene_structure_help = """<html>This panel is recommended for <b>mid-revision</b> stage after the writer has already completed the first draft and implemented early, high-level developmental changes.
<br/>During mid-revision, the writer might refine scene structure to ensure tension, escalation, and reader engagement.
"""

home_page_welcome_text = """Plotlyst is an indie novel writing software created by a solo developer with passion for writing and storytelling.

It offers a range of tools to support various stages of novel writing, including outlining and planning, drafting, and early, mid, or late-stage revisions.

Not every tool needs to be used right away. Several features prove most beneficial after the initial drafting phase.
"""

character_roles_description: Dict[Role, str] = {
    protagonist_role: """
    The central character around whom the story revolves.
    <p>Protagonists often drive the narrative and face significant challenges, having the most at stake.
    <br>They may undergo personal growth, development, or transformation by the end of the story.
    <p>Note that the protagonist may not always have a point of view.
    """,
    antagonist_role: """
    The character who opposes the protagonist most, often creating the central conflict in the story.
    <p>While often referred to as the villain, the antagonist is not necessarily an evil or immoral character. They may have complex motives or goals that drive their actions.
    """,
    major_role: """
    Central character who plays a significant role in impacting the story.<br>They might undergo character development and growth themselves.
    <p>For major but more specific roles see protagonist and antagonist.
    """,
    secondary_role: """An important character who contributes to the story and possibly to the protagonist's character development.
    <br>They may have their own subplots and character arcs but they are not the primary focus.
    <p>Subcategories include sidekick, love interest, guide, supporter/adversary, and contagonist.
    <p>If promoted, they become the deuteragonist - the second most important character role.
    """,
    tertiary_role: """
    Minor characters with limited appearance and impact in the story.
    <br>They may still serve specific functions such as providing information, setting the plot in motion, acting as red herrings, or enhancing the setting and atmosphere.
    <p>For special, adversary tertiary characters, see hecklers.
    """,

    love_interest_role: """
    A character that introduces a romantic subplot or relationship into the story.
    <br>This role not only explores romantic dynamics but often reveals a softer or more vulnerable side of the protagonist.
    <p>In the romance genre, the love interest may assume a more prominent, major role.
    """,

    adversary_role: """
    Characters who oppose the protagonist. While not as central as the antagonist, they still present challenges and tension to the protagonist.
    <p>For a more formidable opposition, see contagonist.
    <p>For lesser, minor adversaries, consider hecklers.
    """,

    supporter_role: """
    A secondary character type who provides support to the protagonist in their journey. They may not fit into more specialized roles like guide, sidekick, or confidant, but they are considered allies.
    <p>Subcategories: Sidekick, Confidant, Guide
    """,
    guide_role: """
    Often referred to as a mentor, this secondary role typically imparts valuable lessons to the protagonist.
    <br>They may share wisdom, knowledge, skills, or provide guidance and direction, be it physical, spiritual, or psychological.
    """,
    confidant_role: """
    Serves as a trusted ally and emotional support, with whom the protagonist can share personal thoughts and feelings.
    <p>Often overlaps with sidekicks, mentors, or love interests.
    <p>This role often implies a deeper personal connection to the protagonist compared to sidekicks.
    """,
    sidekick_role: """
    A loyal companion and supporter to the protagonist, actively participating in their adventures.
    <p>They may have a strong, dynamic relationship with the protagonist, often bringing unique skills or qualities that complement the protagonist's abilities.
    """,

    contagonist_role: """
    An adversary role who works against the protagonist. Unlike the antagonist, the contagonist may have a more ambiguous or conflicted role.
    <p>Contagonists often possess a mix of qualities aligning with both the protagonist and antagonist.
    <p>They may, at times, assist the protagonist and, at other times, hinder their progress. This ambivalence adds complexity to their character, challenging the protagonist in unexpected ways.
    <p>They may be willing to unite with the antagonist, even if their goals differ.
    """,

    foil_role: """
    A mirror character who contrasts with the protagonist, highlighting specific traits, values, or beliefs.
    <br>The foil serves to emphasize differences, offering a profound understanding of the main character's qualities.
    <p>It can contribute to character development or thematic exploration.
    """,
    henchmen_role: """
    Minor adversary characters who subtly obstruct or challenge the protagonist.
    <p>Their role is to introduce layers of opposition and complexity to the story, providing the protagonist with smaller challenges to overcome.
    """
}


@dataclass
class CharacterRoleExample:
    name: str
    title: str
    icon: str = ''
    display_title: bool = True


Harry_Potter = 'Harry Potter'
Hunger_Games = 'Hunger Games'
Lord_of_the_rings = 'Lord of the Rings'
Matrix = 'Matrix'


def character_role_examples(role: Role) -> List[CharacterRoleExample]:
    if role == protagonist_role:
        return [
            CharacterRoleExample('Katniss', Hunger_Games, 'mdi6.bow-arrow'),
            CharacterRoleExample('Harry Potter', Harry_Potter, 'ei.magic', False),
            CharacterRoleExample('Frodo', Lord_of_the_rings, 'fa5s.ring', False),
            CharacterRoleExample('Neo', Matrix, 'mdi.sunglasses', False),
            CharacterRoleExample('Anne', 'of Green Gables', 'mdi.flower'),
            CharacterRoleExample('Hamlet', 'Hamlet', 'fa5s.skull'),
            CharacterRoleExample('Sherlock Holmes', 'Sherlock Holmes', 'mdi.incognito', False)
        ]
    elif role == antagonist_role:
        return [
            CharacterRoleExample('Sauron', Lord_of_the_rings, 'fa5s.ring'),
            CharacterRoleExample('The Joker', 'Batman', 'fa5s.theater-masks'),
            CharacterRoleExample('Voldemort', Harry_Potter, 'ei.magic'),
            CharacterRoleExample('Agent Smith', 'Matrix', 'mdi.sunglasses'),
        ]
    elif role == major_role:
        return [
            CharacterRoleExample('Han Solo', 'Star Wars', 'mdi.death-star-variant'),
            CharacterRoleExample('Aragorn', Lord_of_the_rings, 'mdi.sword'),
            CharacterRoleExample('Griffith', 'Berserk', 'ph.sword-light'),
            CharacterRoleExample('Sasuke', 'Naruto', 'mdi.eye-circle-outline'),
        ]
    elif role == secondary_role:
        return [
            CharacterRoleExample('Luna Lovegood', Harry_Potter, 'ei.magic'),
            CharacterRoleExample('Gimli', Lord_of_the_rings, 'mdi6.axe-battle'),
            CharacterRoleExample('Peeta', Hunger_Games, 'mdi.bread-slice'),
        ]
    elif role == tertiary_role:
        return [
            CharacterRoleExample('Tom Bombadil', Lord_of_the_rings, 'mdi.nature'),
            CharacterRoleExample('Padma and Parvati Patil', Harry_Potter, 'ei.magic'),
            CharacterRoleExample('Wormtail', Harry_Potter, 'ei.magic'),
        ]
    elif role == love_interest_role:
        return [
            CharacterRoleExample('Will', 'Me Before You', 'ei.wheelchair'),
            CharacterRoleExample('Mr Darcy', 'Pride and Prejudice', ''),
            CharacterRoleExample('Mr Rochester', 'Jane Eyre', ''),
            CharacterRoleExample('Mary Jane', 'Spiderman', 'fa5s.spider'),
            CharacterRoleExample('Augustus', 'The Fault in Our Stars', 'ei.star'),
        ]
    elif role == guide_role:
        return [
            CharacterRoleExample('Dumbledore', Harry_Potter, 'ei.magic'),
            CharacterRoleExample('Gandalf', Lord_of_the_rings, 'fa5s.hat-wizard'),
            CharacterRoleExample('Haymitch', Hunger_Games, 'fa5s.wine-glass-alt'),
            CharacterRoleExample('Morpheus', 'Matrix', 'mdi.sunglasses'),
        ]
    elif role == sidekick_role:
        return [
            CharacterRoleExample('Ron', Harry_Potter, 'mdi.rodent'),
            CharacterRoleExample('Robin', 'Batman', 'fa5s.mask'),
            CharacterRoleExample('Dr. Watson', 'Sherlock Holmes', 'mdi.incognito'),
            CharacterRoleExample('Donkey', 'Shrek', 'mdi.donkey'),
        ]
    elif role == confidant_role:
        return [
            CharacterRoleExample('Samwise Gamgee', Lord_of_the_rings, 'fa5s.ring'),
            CharacterRoleExample('Wilson', 'House, M.D.', 'fa5s.briefcase-medical'),
            CharacterRoleExample('Horatio', 'Hamlet', 'fa5s.skull'),
        ]
    elif role == supporter_role:
        return [
            CharacterRoleExample('Legolas', Lord_of_the_rings, 'mdi6.bow-arrow'),
            CharacterRoleExample('Merry and Pippin', Lord_of_the_rings, 'mdi.smoking-pipe'),
            CharacterRoleExample('Luna Lovegood', Harry_Potter, 'ei.magic'),
        ]
    elif role == adversary_role:
        return [
            CharacterRoleExample('Nazgûl', Lord_of_the_rings, 'mdi6.horse-human'),
            CharacterRoleExample('Wormtongue', Lord_of_the_rings, 'fa5s.ring'),
            CharacterRoleExample('Umbridge', Harry_Potter, 'ei.magic'),
        ]
    elif role == contagonist_role:
        return [
            CharacterRoleExample('Severus Snape', Harry_Potter, 'ei.magic'),
            CharacterRoleExample('Gollum', Lord_of_the_rings, 'fa5s.ring'),
            CharacterRoleExample('Jaime Lannister', 'Game of Thrones', 'ri.sword-line'),
        ]
    elif role == foil_role:
        return [
            CharacterRoleExample('Draco Malfoy', Harry_Potter, 'ei.magic'),
            CharacterRoleExample('Tom Buchanan', 'The Great Gatsby', ''),
            CharacterRoleExample('Edgar Linton', 'Wuthering Heights', 'mdi.weather-windy-variant'),
            CharacterRoleExample('George Wickham', 'Pride and Prejudice', ''),
        ]
    elif role == henchmen_role:
        return [
            CharacterRoleExample('Crabbe and Goyle', Harry_Potter, 'ei.magic'),
            CharacterRoleExample('Dudley', Harry_Potter, 'ei.magic'),
            CharacterRoleExample('Orcs', Lord_of_the_rings, 'fa5s.ring'),
            CharacterRoleExample('Stormtroopers', 'Star Wars', 'mdi.death-star-variant'),
        ]

    return []


synopsis_editor_placeholder = "Summarize your story's main events"

WELCOME_DOC_CONTENT: str = '''
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
<html><head><meta name="qrichtext" content="1" /><meta charset="utf-8" /><style type="text/css">
p, li { white-space: pre-wrap; }
hr { height: 1px; border-width: 0; }
li.unchecked::marker { content: "\2610"; }
li.checked::marker { content: "\2612"; }
</style></head><body style=" font-family:'Fira Sans Semi-Light'; font-size:12pt; font-weight:400; font-style:normal;">
<h1 style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; line-height:150%;"><span style=" font-size:xx-large; font-weight:700;">Welcome to Plotlyst</span></h1>
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; line-height:150%;">This is the Documents panel where you can add additional notes.</p>
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; line-height:150%;">If you've purchased <a href="https://plotlyst.com/pricing"><span style=" text-decoration: underline; color:#4B0763;">Plotlyst</span></a>, you can also create Mindmaps here.</p></body></html>
'''
