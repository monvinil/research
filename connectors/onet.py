"""O*NET Web Services connector.

Key data for the research engine:
- Task-level occupation data for Polanyi classification (T21)
- Work activities with importance/level scores
- Technology skills for AI adoption indicators
- Abilities and knowledge for judgment vs prediction decomposition (T22)

Polanyi's Paradox (Autor): We can know more than we can tell.
- Routine-cognitive tasks → automatable by AI (Baumol Cure, T3A)
- Tacit-manual tasks → human premium rises (Baumol Premium, T3B)
- Tacit-cognitive tasks → judgment premium (AGG complement, T22)

O*NET classifies occupations using the Acemoglu-Autor framework:
- Routine Cognitive: Processing info, record keeping, data entry
- Non-routine Cognitive Analytical: Analyzing, interpreting, deciding
- Non-routine Cognitive Interpersonal: Negotiating, coaching, persuading
- Routine Manual: Controlling machines, repetitive physical tasks
- Non-routine Manual: Caring, assisting, operating in unstructured environments

API docs: https://services.onetcenter.org/reference/
Free key: https://services.onetcenter.org/developer
Rate limit: ~50 requests/minute (throttled, not hard-blocked)
"""

import requests
import time
from .config import ONET_API_KEY

BASE_URL = 'https://services.onetcenter.org/ws/'

# Acemoglu-Autor task classification via O*NET Work Activity IDs
# Maps O*NET Generalized Work Activity (GWA) element IDs to Polanyi categories
POLANYI_CLASSIFICATION = {
    'routine_cognitive': {
        'description': 'Automatable by AI — Baumol Cure targets (T3A)',
        'gwa_elements': {
            '4.A.2.a.2': 'Processing Information',
            '4.A.2.a.3': 'Evaluating Information to Determine Compliance',
            '4.A.2.b.1': 'Interacting With Computers',
            '4.A.3.b.1': 'Performing Administrative Activities',
            '4.A.2.a.4': 'Analyzing Data or Information',
            '4.A.3.b.4': 'Documenting/Recording Information',
        },
    },
    'nonroutine_cognitive_analytical': {
        'description': 'Judgment premium — AGG complement (T22)',
        'gwa_elements': {
            '4.A.2.b.2': 'Making Decisions and Solving Problems',
            '4.A.2.b.4': 'Developing Objectives and Strategies',
            '4.A.2.a.1': 'Getting Information',
            '4.A.2.b.3': 'Thinking Creatively',
            '4.A.4.a.4': 'Estimating Quantifiable Characteristics',
            '4.A.2.b.6': 'Updating and Using Relevant Knowledge',
        },
    },
    'nonroutine_cognitive_interpersonal': {
        'description': 'Human premium — relationship/trust moat (T3B)',
        'gwa_elements': {
            '4.A.4.a.5': 'Selling or Influencing Others',
            '4.A.4.b.4': 'Guiding, Directing, and Motivating Subordinates',
            '4.A.4.b.5': 'Coaching and Developing Others',
            '4.A.4.a.6': 'Resolving Conflicts and Negotiating',
            '4.A.4.a.1': 'Communicating with Supervisors, Peers, or Subordinates',
            '4.A.4.b.3': 'Coordinating the Work and Activities of Others',
        },
    },
    'routine_manual': {
        'description': 'Robotics frontier — slower automation timeline',
        'gwa_elements': {
            '4.A.3.a.2': 'Controlling Machines and Processes',
            '4.A.3.a.3': 'Operating Vehicles, Mechanized Devices, or Equipment',
            '4.A.3.a.4': 'Inspecting Equipment, Structures, or Materials',
            '4.A.1.b.2': 'Handling and Moving Objects',
        },
    },
    'nonroutine_manual': {
        'description': 'Human-only — unstructured physical + empathy',
        'gwa_elements': {
            '4.A.4.a.8': 'Assisting and Caring for Others',
            '4.A.1.a.2': 'Performing General Physical Activities',
            '4.A.3.b.5': 'Performing for or Working Directly with the Public',
        },
    },
}

# Build reverse lookup: element_id → (category, activity_name)
_ELEMENT_TO_CATEGORY = {}
for _cat, _info in POLANYI_CLASSIFICATION.items():
    for _eid, _name in _info['gwa_elements'].items():
        _ELEMENT_TO_CATEGORY[_eid] = (_cat, _name)

# Key occupations for landscape mapping — covers major Baumol sectors
# SOC codes use O*NET format (XX-XXXX.XX)
KEY_OCCUPATIONS = {
    # High-wage cognitive (Baumol Cure prime targets)
    '23-1011.00': 'Lawyers',
    '23-2011.00': 'Paralegals and Legal Assistants',
    '13-2011.00': 'Accountants and Auditors',
    '13-1111.00': 'Management Analysts',
    '15-1252.00': 'Software Developers',
    '15-2051.00': 'Data Scientists',
    '29-1141.00': 'Registered Nurses',
    '29-1228.00': 'Physicians, All Other',
    '25-1011.00': 'Business Teachers, Postsecondary',
    '11-1021.00': 'General and Operations Managers',

    # Mid-wage cognitive (underexplored Baumol territory)
    '43-3031.00': 'Bookkeeping, Accounting, and Auditing Clerks',
    '43-4051.00': 'Customer Service Representatives',
    '43-9061.00': 'Office Clerks, General',
    '13-2082.00': 'Tax Preparers',
    '29-2052.00': 'Pharmacy Technicians',
    '43-6014.00': 'Secretaries and Administrative Assistants',
    '41-3021.00': 'Insurance Sales Agents',
    '13-1071.00': 'Human Resources Specialists',
    '27-3031.00': 'Public Relations Specialists',

    # Manual/hybrid (Baumol Premium candidates)
    '31-1120.00': 'Home Health and Personal Care Aides',
    '35-2014.00': 'Cooks, Restaurant',
    '47-2061.00': 'Construction Laborers',
    '53-3032.00': 'Heavy and Tractor-Trailer Truck Drivers',
    '37-2011.00': 'Janitors and Cleaners',
    '39-9011.00': 'Childcare Workers',
    '33-9032.00': 'Security Guards',

    # Emerging/hybrid (AI-native candidates)
    '15-1299.08': 'Computer Systems Engineers/Architects',
    '13-1161.00': 'Market Research Analysts',
    '27-1024.00': 'Graphic Designers',
    '15-1232.00': 'Computer User Support Specialists',
}


class ONetConnector:
    """Pull occupation and task data from O*NET Web Services for Polanyi classification."""

    def __init__(self, api_key=None):
        self.api_key = api_key or ONET_API_KEY
        self.base_url = BASE_URL
        self._last_request_time = 0
        self._min_interval = 1.2  # seconds between requests (respect rate limits)

    def _get(self, endpoint, params=None):
        """O*NET uses HTTP Basic Auth (username=key, password=empty)."""
        if not self.api_key:
            raise RuntimeError(
                'O*NET API key required. Get one free at '
                'https://services.onetcenter.org/developer and add '
                'ONET_API_KEY to your .env file.'
            )

        # Rate limiting
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)

        url = f'{self.base_url}{endpoint}'
        headers = {'Accept': 'application/json'}

        r = requests.get(
            url,
            params=params,
            headers=headers,
            auth=(self.api_key, ''),
            timeout=15,
        )
        self._last_request_time = time.time()

        if r.status_code == 422:
            return {'error': 'invalid_code', 'detail': r.text}
        r.raise_for_status()
        return r.json()

    # ── Core data retrieval ──────────────────────────────────────────

    def get_occupation_details(self, soc_code):
        """Get basic occupation info (title, description, sample tasks)."""
        return self._get(f'online/occupations/{soc_code}')

    def get_tasks(self, soc_code):
        """Get all tasks for an occupation with importance scores.

        Returns task statements + relevance/importance ratings.
        Critical for Polanyi classification — each task is classifiable.
        """
        return self._get(f'online/occupations/{soc_code}/summary/tasks')

    def get_work_activities(self, soc_code):
        """Get Generalized Work Activities (GWAs) with importance and level scores.

        These map directly to Acemoglu-Autor task categories via POLANYI_CLASSIFICATION.
        """
        return self._get(f'online/occupations/{soc_code}/summary/work_activities')

    def get_detailed_work_activities(self, soc_code):
        """Get Detailed Work Activities (DWAs) — finer-grained than GWAs."""
        return self._get(f'online/occupations/{soc_code}/summary/detailed_work_activities')

    def get_technology_skills(self, soc_code):
        """Get technology skills for an occupation.

        Indicators of current tech adoption and AI integration potential.
        Occupations already using data tools are closer to AI augmentation.
        """
        return self._get(f'online/occupations/{soc_code}/summary/technology_skills')

    def get_knowledge(self, soc_code):
        """Get knowledge requirements — distinguishes codified vs tacit knowledge."""
        return self._get(f'online/occupations/{soc_code}/summary/knowledge')

    def get_abilities(self, soc_code):
        """Get cognitive and physical abilities — maps to judgment vs prediction."""
        return self._get(f'online/occupations/{soc_code}/summary/abilities')

    def get_skills(self, soc_code):
        """Get skills with importance/level — broad competency profile."""
        return self._get(f'online/occupations/{soc_code}/summary/skills')

    def search_occupations(self, keyword, start=1, end=20):
        """Search occupations by keyword."""
        return self._get('online/search', params={
            'keyword': keyword,
            'start': start,
            'end': end,
        })

    # ── Polanyi Classification Engine ────────────────────────────────

    def classify_polanyi(self, soc_code):
        """Derive Polanyi task classification for an occupation.

        Uses Acemoglu-Autor framework applied to O*NET work activity data.
        Returns category scores, dominant category, and automation exposure estimate.

        Output structure:
        {
            'soc_code': '13-2011.00',
            'title': 'Accountants and Auditors',
            'category_scores': {
                'routine_cognitive': 72.5,          ← automatable
                'nonroutine_cognitive_analytical': 45.2,  ← judgment premium
                'nonroutine_cognitive_interpersonal': 30.1,  ← human premium
                'routine_manual': 5.0,
                'nonroutine_manual': 2.0,
            },
            'dominant_category': 'routine_cognitive',
            'polanyi_label': 'Routine-Cognitive (Automatable)',
            'automation_exposure': 0.68,  ← 0-1 scale
            'judgment_premium': 0.32,     ← AGG complement value
            'human_premium': 0.21,        ← Baumol Premium value
            'theory_mapping': {
                'T3A_baumol_cure': True,  ← high routine-cognitive
                'T3B_baumol_premium': False,
                'T22_judgment_complement': True,  ← significant analytical
            }
        }
        """
        # Get work activities with importance/level scores
        wa_data = self.get_work_activities(soc_code)
        if 'error' in wa_data:
            return wa_data

        # Get occupation title
        occ_data = self.get_occupation_details(soc_code)
        title = occ_data.get('title', soc_code)

        # Score each Polanyi category based on matched work activities
        category_scores = {}
        matched_activities = {}

        for activity in wa_data.get('element', wa_data.get('work_activity', [])):
            element_id = activity.get('id', '')
            importance = _extract_score(activity, 'Importance')
            level = _extract_score(activity, 'Level')
            name = activity.get('name', '')

            if element_id in _ELEMENT_TO_CATEGORY:
                cat, _ = _ELEMENT_TO_CATEGORY[element_id]
                # Combined score: importance × level gives weighted task intensity
                score = (importance or 0) * (level or 0)
                category_scores.setdefault(cat, 0)
                category_scores[cat] += score
                matched_activities.setdefault(cat, [])
                matched_activities[cat].append({
                    'name': name,
                    'importance': importance,
                    'level': level,
                    'score': score,
                })

        # Normalize scores to 0-100 scale
        max_score = max(category_scores.values()) if category_scores else 1
        if max_score > 0:
            for cat in category_scores:
                category_scores[cat] = round(category_scores[cat] / max_score * 100, 1)

        # Derive aggregate metrics
        rc = category_scores.get('routine_cognitive', 0)
        nca = category_scores.get('nonroutine_cognitive_analytical', 0)
        nci = category_scores.get('nonroutine_cognitive_interpersonal', 0)
        rm = category_scores.get('routine_manual', 0)
        nm = category_scores.get('nonroutine_manual', 0)

        total = rc + nca + nci + rm + nm or 1

        automation_exposure = round((rc + rm * 0.5) / total, 2)
        judgment_premium = round(nca / total, 2)
        human_premium = round((nci + nm) / total, 2)

        # Determine dominant category
        dominant = max(category_scores, key=category_scores.get) if category_scores else 'unknown'

        labels = {
            'routine_cognitive': 'Routine-Cognitive (Automatable)',
            'nonroutine_cognitive_analytical': 'Non-routine Analytical (Judgment Premium)',
            'nonroutine_cognitive_interpersonal': 'Non-routine Interpersonal (Human Premium)',
            'routine_manual': 'Routine-Manual (Robotics Frontier)',
            'nonroutine_manual': 'Non-routine Manual (Human-Only)',
        }

        return {
            'soc_code': soc_code,
            'title': title,
            'category_scores': category_scores,
            'dominant_category': dominant,
            'polanyi_label': labels.get(dominant, 'Unknown'),
            'automation_exposure': automation_exposure,
            'judgment_premium': judgment_premium,
            'human_premium': human_premium,
            'theory_mapping': {
                'T3A_baumol_cure': rc > 40,
                'T3B_baumol_premium': nci > 30 or nm > 30,
                'T22_judgment_complement': nca > 35,
                'T21_polanyi_tacit': (nca + nci + nm) > (rc + rm),
            },
            'matched_activities': matched_activities,
        }

    def screen_occupations(self, soc_codes=None):
        """Bulk Polanyi classification across key occupations.

        Returns a sorted list by automation exposure — highest exposure first.
        These are the prime Baumol Cure targets for landscape mapping.
        """
        targets = soc_codes or KEY_OCCUPATIONS

        results = []
        errors = []

        for soc_code in targets:
            try:
                classification = self.classify_polanyi(soc_code)
                if 'error' in classification:
                    errors.append({'soc_code': soc_code, 'error': classification['error']})
                    continue
                classification['occupation_label'] = targets.get(soc_code, soc_code) if isinstance(targets, dict) else soc_code
                results.append(classification)
            except Exception as e:
                errors.append({'soc_code': soc_code, 'error': str(e)})

        # Sort by automation exposure (highest first = biggest Baumol Cure targets)
        results.sort(key=lambda x: x.get('automation_exposure', 0), reverse=True)

        return {
            'signal_type': 'polanyi_occupation_screen',
            'theory': 'T21 (Polanyi), T3A/T3B (Baumol), T22 (AGG)',
            'occupations_screened': len(results),
            'errors': errors,
            'results': results,
            'interpretation': (
                'Occupations sorted by automation exposure. Top entries are prime '
                'Baumol Cure targets (T3A) — high routine-cognitive content that AI '
                'can replace. Bottom entries with high human_premium are Baumol Premium '
                'candidates (T3B) — services that become MORE valuable as AI handles '
                'the routine. Middle entries with high judgment_premium are AGG '
                'complement plays (T22) — prediction automates but judgment stays human.'
            ),
        }

    def get_automation_profile(self, soc_code):
        """Deep automation profile combining tasks, activities, tech skills, and abilities.

        More detailed than classify_polanyi — use for Agent B deep dives on
        specific opportunities.
        """
        tasks = self.get_tasks(soc_code)
        classification = self.classify_polanyi(soc_code)
        tech = self.get_technology_skills(soc_code)
        abilities = self.get_abilities(soc_code)

        if 'error' in classification:
            return classification

        # Extract task statements for context
        task_list = []
        for t in tasks.get('task', tasks.get('element', [])):
            task_list.append({
                'statement': t.get('statement', t.get('name', '')),
                'importance': _extract_score(t, 'Importance'),
            })

        # Extract technology tools
        tech_tools = []
        for t in tech.get('technology', tech.get('element', [])):
            tech_tools.append({
                'name': t.get('name', ''),
                'hot_technology': t.get('hot_technology', False),
            })

        # Extract cognitive vs physical abilities
        cognitive_abilities = []
        physical_abilities = []
        for a in abilities.get('ability', abilities.get('element', [])):
            name = a.get('name', '')
            importance = _extract_score(a, 'Importance')
            entry = {'name': name, 'importance': importance}
            # O*NET cognitive ability IDs start with 1.A.1, physical with 1.A.3
            aid = a.get('id', '')
            if aid.startswith('1.A.1') or aid.startswith('1.A.2'):
                cognitive_abilities.append(entry)
            elif aid.startswith('1.A.3'):
                physical_abilities.append(entry)

        return {
            'soc_code': soc_code,
            'title': classification.get('title', soc_code),
            'polanyi_classification': classification,
            'tasks': task_list,
            'technology_tools': tech_tools,
            'cognitive_abilities': cognitive_abilities,
            'physical_abilities': physical_abilities,
            'ai_readiness_indicators': {
                'high_routine_cognitive': classification.get('automation_exposure', 0) > 0.5,
                'already_using_tech': len(tech_tools) > 5,
                'low_physical_requirement': len(physical_abilities) < 3,
                'high_judgment_need': classification.get('judgment_premium', 0) > 0.3,
            },
        }

    # ── Connection test ──────────────────────────────────────────────

    def test_connection(self):
        """Verify O*NET API access."""
        try:
            result = self.get_occupation_details('13-2011.00')  # Accountants
            if 'error' in result:
                return {'status': 'error', 'source': 'O*NET', 'error': result}
            return {
                'status': 'ok',
                'source': 'O*NET',
                'authenticated': True,
                'test_occupation': result.get('title', 'Accountants and Auditors'),
                'api_version': 'Web Services v2',
            }
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                return {
                    'status': 'error',
                    'source': 'O*NET',
                    'error': 'Authentication failed. Check ONET_API_KEY in .env',
                }
            return {'status': 'error', 'source': 'O*NET', 'error': str(e)}
        except Exception as e:
            return {'status': 'error', 'source': 'O*NET', 'error': str(e)}


def _extract_score(element, scale_name):
    """Extract a score value from O*NET's nested scale structure.

    O*NET returns scores as: {'scale': {'id': 'IM', 'name': 'Importance'}, 'value': 3.5}
    nested within a 'score' list on each element.
    """
    for score in element.get('score', element.get('scales', [])):
        if isinstance(score, dict):
            scale = score.get('scale', {})
            if isinstance(scale, dict) and scale.get('name') == scale_name:
                return score.get('value')
            # Flat structure fallback
            if score.get('name') == scale_name:
                return score.get('value')
    return None
