"""
Plotlyst
Copyright (C) 2021-2022  Zsolt Kovari

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
from src.main.python.plotlyst.core.domain import enneagram_field

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
