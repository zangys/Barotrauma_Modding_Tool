import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeAlias

from Code.xml_object import XMLElement

logger = logging.getLogger(__name__)

StackItem: TypeAlias = Tuple[XMLElement, bool, Optional[str]]
IDParserUnitType: TypeAlias = "IDParserUnit"

HandlerType: TypeAlias = Callable[[XMLElement, List[StackItem], bool, IDParserUnitType, Optional[str]], None]


@dataclass(slots=True)
class IDParserUnit:
    add_id: Set[str] = field(default_factory=set)
    override_id: Set[str] = field(default_factory=set)

    @staticmethod
    def create_empty() -> "IDParserUnit":
        return IDParserUnit()


class IDExtractor:
    def __init__(self):
        self._unknown_tags_cache: Set[str] = set()
        pass

    def extract_ids(self, root_obj: Optional[XMLElement]) -> IDParserUnit:
        if root_obj is None:
            return IDParserUnit.create_empty()
        tag_lower = root_obj.tag.lower()
        if tag_lower in ("infotext", "infotexts", "contentpackage", "english"):
            return IDParserUnit.create_empty()

        result_unit = IDParserUnit.create_empty()
        self._parse_loop(root_obj, result_unit)
        return result_unit

    def _parse_loop(self, root: XMLElement, unit: IDParserUnit):
        stack: List[StackItem] = [(root, False, None)]
        rules_get = _RULES.get
        unknown_cache = self._unknown_tags_cache
        
        while stack:
            obj, is_override, ctx = stack.pop()
            
            tag_lower = obj.tag.lower()

            rule = rules_get(tag_lower)
            if rule:
                rule(obj, stack, is_override, unit, ctx)
                continue

            if ctx:
                context_rule = rules_get(ctx)
                if context_rule:
                    context_rule(obj, stack, is_override, unit, ctx)
                    continue

            self._handle_fallback(obj, is_override, unit, unknown_cache)

    def _handle_fallback(self, obj: XMLElement, is_override: bool, unit: IDParserUnit, cache: Set[str]):
        anim_type = obj.attributes.get("animationtype")
        if not anim_type:
            anim_type = obj.get_attribute_ignore_case("animationtype")

        if not anim_type:
            if obj.tag not in cache:
                cache.add(obj.tag)
            return

        res: Optional[str] = None
        at_lower = anim_type.lower()
        
        if at_lower in ("swimslow", "swimfast"):
            res = f"WaterAnimation.{obj.tag}"
        elif at_lower in ("walk", "run", "crouch"):
            res = f"GroundAnimation.{obj.tag}"

        if res:
            (unit.override_id if is_override else unit.add_id).add(res)


def _make_context_rule(context_type: Optional[str] = None) -> HandlerType:
    def _rule(
        obj: XMLElement,
        stack: List[StackItem],
        is_override: bool,
        _: IDParserUnit,
        current_context: Optional[str],
    ):
        next_ctx = context_type if context_type else current_context
        for child in obj.iter_non_comment_childrens():
            stack.append((child, is_override, next_ctx))
    return _rule


def _make_override_rule() -> HandlerType:
    def _rule(
        obj: XMLElement,
        stack: List[StackItem],
        _curr: bool,
        _: IDParserUnit,
        current_context: Optional[str],
    ):
        for child in obj.iter_non_comment_childrens():
            stack.append((child, True, current_context))
    return _rule


def _make_id_rule(prefix: str, id_field: str = "identifier") -> HandlerType:
    def _rule(
        obj: XMLElement,
        _stack: List[StackItem],
        is_override: bool,
        unit: IDParserUnit,
        _ctx: Any,
    ):
        identifier = obj.attributes.get(id_field) or obj.tag
        full_id = f"{prefix}.{identifier}"
        (unit.override_id if is_override else unit.add_id).add(full_id)
    return _rule


def _make_special_id_rule(name: str) -> HandlerType:
    def _rule(
        _obj: XMLElement,
        _stack: List[StackItem],
        is_override: bool,
        unit: IDParserUnit,
        _ctx: Any,
    ):
        (unit.override_id if is_override else unit.add_id).add(name)
    return _rule


def _ignore_rule(*args, **kwargs):
    pass


_RULES: Dict[str, HandlerType] = {
    "override": _make_override_rule(),
    
    "english": _ignore_rule,
    "infotexts": _ignore_rule,
    "infotext": _ignore_rule,
    "contentpackage": _ignore_rule,
    "documentation": _ignore_rule,
    "metadata": _ignore_rule,
    "vars": _ignore_rule,
    "sounds": _ignore_rule,
    "names": _ignore_rule,
    "particles": _ignore_rule,
    "ai": _ignore_rule,
    "body": _ignore_rule,
    "holdable": _ignore_rule,

    "items": _make_context_rule("item"),
    "item": _make_id_rule("item"),
    "afflictions": _make_context_rule("affliction"),
    "affliction": _make_id_rule("affliction"),
    "cprsettings": _make_special_id_rule("CPRSettings"),

    "character": _make_id_rule("Character", "speciesname"),
    "characters": _make_context_rule(),
    "monsters": _make_context_rule("monster"),
    "monster": _make_id_rule("Character", "speciesname"),
    "ragdoll": _make_id_rule("Ragdoll", "type"),
    "ballastflorabehavior": _make_id_rule("BallastFlora", "identifier"),

    "huskappendage": _make_context_rule(),
    "limb": _make_id_rule("HuskAppendage.limb", "name"),
    "joint": _make_id_rule("HuskAppendage.joint", "name"),

    "levelobjects": _make_context_rule("levelobjects"),
    "levelobject": _make_id_rule("LevelObject"),
    "itemassembly": _make_id_rule("ItemAssembly", "name"),
    "upgrademodules": _make_context_rule(),
    "upgrademodule": _make_id_rule("UpgradeModule"),
    "upgradecategory": _make_id_rule("UpgradeCategory"),

    "talenttrees": _make_context_rule(),
    "talenttree": _make_id_rule("TalentTree", "jobidentifier"),
    "talents": _make_context_rule(),
    "talent": _make_id_rule("Talent"),
    "jobs": _make_context_rule(),
    "job": _make_id_rule("Job"),

    "corpses": _make_context_rule(),
    "corpse": _make_id_rule("Corpse"),
    "style": _make_special_id_rule("Style"),
    "backgroundcreatures": _make_context_rule("backgroundcreature"),
    "backgroundcreature": _make_id_rule("BackgroundCreature", ""),

    "randomevents": _make_context_rule(),
    "eventset": _make_id_rule("EventSet"),
    "missions": _make_context_rule("mission"),
    "mission": _make_context_rule("Mission"),

    "abandonedoutpostmission": _make_id_rule("Mission.Outpost"),
    "crawlerlairmission": _make_id_rule("Mission.AbandonedOutpost"),
    "salvagemission": _make_id_rule("Mission.Salvage"),
    "monstermission": _make_id_rule("Mission.Monster"),
    "piratemission": _make_id_rule("Mission.Pirate"),
    "mudraptorlairmission": _make_id_rule("Mission.MudraptorLair"),
    "thresherlairmission": _make_id_rule("Mission.ThresherLair"),
    "huskcrawlerlairmission": _make_id_rule("Mission.HuskCrawlerLair"),
    "outpostdestroymission": _make_id_rule("Mission.OutpostDestroy"),
    "mineralmission": _make_id_rule("Mission.Mineral"),
    "gotomission": _make_id_rule("Mission.Goto"),
    "escortmission": _make_id_rule("Mission.Escort"),
    "outpostmission": _make_id_rule("Mission.Outpost"),
    "cargomission": _make_id_rule("Mission.Cargo"),

    "eventprefabs": _make_context_rule(),
    "scriptedevent": _make_id_rule("ScriptedEvent"),
    "triggerevent": _make_id_rule("TriggerEvent"),

    "cavegenerationparameters": _make_context_rule(),
    "cave": _make_id_rule("Cave"),
    "outpostgenerationparameters": _make_context_rule(),
    "outpostconfig": _make_id_rule("OutpostConfig"),
    "mapgenerationparameters": _make_special_id_rule("MapGenerationParameters"),

    "orders": _make_context_rule(),
    "order": _make_id_rule("Order"),
    "factions": _make_context_rule(),
    "faction": _make_id_rule("Faction"),
    "levelgenerationparameters": _make_context_rule("levelgenerationparameter"),
    "levelgenerationparameter": _make_id_rule("LevelGenerationParameter"),
    "biomes": _make_context_rule("biome"),
    "biome": _make_id_rule("Biome"),
    "locationtypes": _make_context_rule("locationtype"),
    "locationtype": _make_id_rule("LocationType"),

    "charactervariant": _make_id_rule("Charactervariant", "speciesname"),
    "wreckaiconfig": _make_id_rule("WreckAIConfig", "Entity"),
    "eventsprites": _make_context_rule("eventsprite"),
    "eventsprite": _make_id_rule("EventSprites"),
    "npcsets": _make_context_rule(),
    "npcset": _make_context_rule("npc"),
    "npc": _make_id_rule("NPC"),
}


_GLOBAL_EXTRACTOR = IDExtractor()

def extract_ids(obj: Optional[XMLElement]) -> IDParserUnit:
    return _GLOBAL_EXTRACTOR.extract_ids(obj)