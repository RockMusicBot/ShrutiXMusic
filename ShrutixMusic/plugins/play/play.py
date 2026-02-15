import random
import re
import string

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InputMediaPhoto, Message
from pytgcalls.exceptions import NoActiveGroupCall

import config
from ShrutixMusic import Apple, Resso, SoundCloud, Spotify, Telegram, YouTube, nand
from ShrutixMusic.core.call import Shruti
from ShrutixMusic.utils import seconds_to_min, time_to_seconds
from ShrutixMusic.utils.channelplay import get_channeplayCB
from ShrutixMusic.utils.decorators.language import languageCB
from ShrutixMusic.utils.decorators.play import PlayWrapper
from ShrutixMusic.utils.formatters import formats
from ShrutixMusic.utils.inline import (
    botplaylist_markup,
    livestream_markup,
    playlist_markup,
    slider_markup,
    track_markup,
)
from ShrutixMusic.utils.logger import play_logs
from ShrutixMusic.utils.stream.stream import stream
from config import BANNED_USERS, lyrical


ILLEGAL_CONTENT_PATTERNS = [
    r'\bdrugs?\b',
    r'\bdrugz?\b',
    r'\bcocaine\b',
    r'\bheroin\b',
    r'\bheroine\b',
    r'\bmeth\b',
    r'\bamphetamine\b',
    r'\bmdma\b',
    r'\becstasy\b',
    r'\blsd\b',
    r'\bmarijuana\b',
    r'\bweed\b',
    r'\bpot\b',
    r'\bganja\b',
    r'\bcharas\b',
    r'\bhash\b',
    r'\bhashish\b',
    r'\bopium\b',
    r'\bafeem\b',
    r'\bsmack\b',
    r'\bcrack\b',
    r'\bnarcotic\b',
    r'\bnarcotics\b',
    r'\bopioid\b',
    r'\bopioids\b',
    r'\bfentanyl\b',
    r'\bketamine\b',
    r'\bpcp\b',
    r'\bpsychedelic\b',
    r'\bpsilocybin\b',
    r'\bmushroom\b',
    r'\bshrooms\b',
    r'\bdmt\b',
    r'\bayahuasca\b',
    r'\bpeyote\b',
    r'\bmescaline\b',
    r'\bsteroids?\b',
    r'\banabolic\b',
    r'\btestosterone\b',
    r'\bhgh\b',
    r'\binhalant\b',
    r'\bsolvent\b',
    r'\bglue\b',
    r'\bpaint\s+thinner\b',
    r'\bwhippets?\b',
    r'\bnitrous\b',
    r'\bpoppers\b',
    r'\bbenzo\b',
    r'\bbenzodiazepine\b',
    r'\bxanax\b',
    r'\bvalium\b',
    r'\bativan\b',
    r'\bklonopin\b',
    r'\bambien\b',
    r'\bpercocet\b',
    r'\boxycontin\b',
    r'\bvicodin\b',
    r'\bcodeine\b',
    r'\bhydrocodone\b',
    r'\bmorphine\b',
    r'\bmethadone\b',
    r'\bsuboxone\b',
    r'\btramadol\b',
    r'\badderall\b',
    r'\britalin\b',
    r'\bconcerta\b',
    r'\bvyvanse\b',
    r'\bmodafinil\b',
    r'\bprovigil\b',
    r'\bnicotine\b',
    r'\btobacco\b',
    r'\bcigarette\b',
    r'\bvape\b',
    r'\be-cig\b',
    r'\bjuul\b',
    r'\balcohol\b',
    r'\bbooze\b',
    r'\bliquor\b',
    r'\bvodka\b',
    r'\bwhiskey\b',
    r'\brum\b',
    r'\bgin\b',
    r'\btequila\b',
    r'\bbeer\b',
    r'\bwine\b',
    r'\bchampagne\b',
    r'\bspice\b',
    r'\bk2\b',
    r'\bbath\s+salt\b',
    r'\bsynthetic\b',
    r'\bdesigner\s+drug\b',
    r'\bresearch\s+chemical\b',
    r'\bghb\b',
    r'\brohypnol\b',
    r'\broofies\b',
    r'\bdate\s+rape\b',
    r'\bkrokodil\b',
    r'\bdesomorphine\b',
    r'\bcarfentanil\b',
    r'\bfentanil\b',
    r'\bu-47700\b',
    r'\bu47700\b',
    r'\bfuranyl\b',
    r'\bacetyl\b',
    r'\bphenazepam\b',
    r'\betizolam\b',
    r'\bflubromazolam\b',
    r'\bclonazolam\b',
    r'\bflualprazolam\b',
    r'\b2c-b\b',
    r'\b2cb\b',
    r'\b25i\b',
    r'\bnbome\b',
    r'\b4-aco\b',
    r'\b4aco\b',
    r'\b5-meo\b',
    r'\b5meo\b',
    r'\bdxm\b',
    r'\bdextromethorphan\b',
    r'\bkratom\b',
    r'\bsalvia\b',
    r'\bibogaine\b',
    r'\bpharma\b',
    r'\bpharmacy\b',
    r'\bprescription\b',
    r'\bpills?\b',
    r'\btablet\b',
    r'\bcapsule\b',
    r'\binjection\b',
    r'\bsyringe\b',
    r'\bneedle\b',
    r'\bsnort\b',
    r'\bsniff\b',
    r'\bsmoke\b',
    r'\binhale\b',
    r'\bshoot\s+up\b',
    r'\bmainline\b',
    r'\bfix\b',
    r'\bhit\b',
    r'\bdose\b',
    r'\btrip\b',
    r'\bhigh\b',
    r'\bstoned\b',
    r'\bbuzzed\b',
    r'\bwasted\b',
    r'\bfaded\b',
    r'\blit\b',
    r'\bblazed\b',
    r'\brolling\b',
    r'\btripping\b',
    r'\bnodding\b',
    r'\bjunkie\b',
    r'\baddict\b',
    r'\bdealer\b',
    r'\bpusher\b',
    r'\bplug\b',
    r'\bconnect\b',
    r'\bsupply\b',
    r'\bscore\b',
    r'\bre-up\b',
    r'\breup\b',
    r'\bpick\s+up\b',
    r'\bcop\b',
    r'\bgrab\b',
    r'\bbuy\b',
    r'\bsell\b',
    r'\btrade\b',
    r'\bstash\b',
    r'\bbag\b',
    r'\bgram\b',
    r'\boz\b',
    r'\bounce\b',
    r'\bkilo\b',
    r'\bbrick\b',
    r'\bbundle\b',
    r'\bdime\b',
    r'\bnickel\b',
    r'\beight\s+ball\b',
    r'\b8ball\b',
    r'\bquarter\b',
    r'\bhalf\b',
    r'\bteener\b',
    r'\bpowder\b',
    r'\brock\b',
    r'\bcrystal\b',
    r'\bglass\b',
    r'\bice\b',
    r'\btina\b',
    r'\bcrank\b',
    r'\bspeed\b',
    r'\buppers\b',
    r'\bdowners\b',
    r'\bbenzo\b',
    r'\bbar\b',
    r'\bxan\b',
    r'\bperc\b',
    r'\boxy\b',
    r'\bblue\b',
    r'\bwhite\b',
    r'\byellow\b',
    r'\bgreen\b',
    r'\bpink\b',
    r'\bred\b',
    r'\bcoke\b',
    r'\bblow\b',
    r'\bsnow\b',
    r'\byayo\b',
    r'\byay\b',
    r'\bwhite\s+girl\b',
    r'\bgirl\b',
    r'\bboy\b',
    r'\bh\b',
    r'\bbrown\b',
    r'\btar\b',
    r'\bchina\s+white\b',
    r'\bblack\s+tar\b',
    r'\bmolly\b',
    r'\bmandy\b',
    r'\badam\b',
    r'\beans\b',
    r'\bx\b',
    r'\be\b',
    r'\bpills\b',
    r'\btabs?\b',
    r'\bacid\b',
    r'\bdot\b',
    r'\bpaper\b',
    r'\bblotter\b',
    r'\bwindowpane\b',
    r'\bmicrodot\b',
    r'\bgelatin\b',
    r'\bliquid\b',
    r'\bbutton\b',
    r'\bcactus\b',
    r'\bmesc\b',
    r'\bspecial\s+k\b',
    r'\bkit\s+kat\b',
    r'\bcat\s+valium\b',
    r'\bvitamin\s+k\b',
    r'\bjet\b',
    r'\bsuper\s+acid\b',
    r'\bgreen\b',
    r'\bpurple\b',
    r'\bk-hole\b',
    r'\bkhole\b',
    r'\bdust\b',
    r'\bangel\s+dust\b',
    r'\bpaz\b',
    r'\bwack\b',
    r'\brocket\s+fuel\b',
    r'\bembalming\s+fluid\b',
    r'\bkiller\s+weed\b',
    r'\bsupergrass\b',
    r'\bsuperweed\b',
    r'\bsherm\b',
    r'\bshermans\b',
    r'\bwet\b',
    r'\bfry\b',
    r'\bill\b',
    r'\bdank\b',
    r'\bkush\b',
    r'\bskunk\b',
    r'\bhydro\b',
    r'\bchronic\b',
    r'\bkief\b',
    r'\bconcentrate\b',
    r'\bshatter\b',
    r'\bwax\b',
    r'\bdab\b',
    r'\boil\b',
    r'\bedible\b',
    r'\bbrownie\b',
    r'\bcookie\b',
    r'\bgummy\b',
    r'\btincture\b',
    r'\btopical\b',
    r'\bcannabis\b',
    r'\bcbd\b',
    r'\bthc\b',
    r'\btetrahydrocannabinol\b',
    r'\bcannabinoid\b',
    r'\bhempt?\b',
    r'\bbud\b',
    r'\bnugs?\b',
    r'\bflower\b',
    r'\bleaf\b',
    r'\btree\b',
    r'\bgrass\b',
    r'\bherb\b',
    r'\bmary\s+jane\b',
    r'\bmj\b',
    r'\brefer\b',
    r'\breefer\b',
    r'\bjoint\b',
    r'\bspliff\b',
    r'\bblunt\b',
    r'\bbowl\b',
    r'\bbong\b',
    r'\bpipe\b',
    r'\bvaporizer\b',
    r'\bvape\s+pen\b',
    r'\bcartridge\b',
    r'\bcart\b',
    r'\bpen\b',
    r'\brig\b',
    r'\bnail\b',
    r'\btorch\b',
    r'\bgrinder\b',
    r'\brolling\s+paper\b',
    r'\bwrap\b',
    r'\bfilter\b',
    r'\broach\b',
    r'\bstoner\b',
    r'\bpothead\b',
    r'\bhead\b',
    r'\bhippie\b',
    r'\brasta\b',
    r'\b420\b',
    r'\b710\b',
    r'\bdispensary\b',
    r'\bbudtender\b',
    r'\bstrain\b',
    r'\bindica\b',
    r'\bsativa\b',
    r'\bhybrid\b',
    r'\bmedical\b',
    r'\brecreational\b',
    r'\bdecriminalize\b',
    r'\blegalize\b',
    r'\bprohibition\b',
    r'\bwar\s+on\s+drugs\b',
    r'\bdrug\s+test\b',
    r'\bpiss\s+test\b',
    r'\bdetox\b',
    r'\brehab\b',
    r'\brecovery\b',
    r'\bsobriety\b',
    r'\bclean\b',
    r'\bsober\b',
    r'\brelapse\b',
    r'\bwithdrawal\b',
    r'\bdetoxification\b',
    r'\boverdose\b',
    r'\bod\b',
    r'\bnaloxone\b',
    r'\bnarcan\b',
    r'\bantidote\b',
    r'\bemergency\b',
    r'\bparaphernalia\b',
    r'\bequipment\b',
    r'\bsupplies\b',
    r'\baccessories\b',
    r'\bscale\b',
    r'\bbaggie\b',
    r'\bplastic\s+bag\b',
    r'\bfoil\b',
    r'\bspoon\b',
    r'\bcooker\b',
    r'\btourniquet\b',
    r'\btie\s+off\b',
    r'\bvein\b',
    r'\btrack\s+mark\b',
    r'\babscess\b',
    r'\binfection\b',
    r'\bdisease\b',
    r'\bhiv\b',
    r'\bhepatitis\b',
    r'\bhep\s+c\b',
    r'\baids\b',
    r'\bstd\b',
    r'\bsti\b',
    r'\bcontaminated\b',
    r'\bdirty\b',
    r'\bused\b',
    r'\bshare\b',
    r'\bshared\b',
    r'\bneedle\s+exchange\b',
    r'\bharm\s+reduction\b',
    r'\bsafe\s+injection\b',
    r'\bshooting\s+gallery\b',
    r'\bcrack\s+house\b',
    r'\bdope\s+house\b',
    r'\btrap\s+house\b',
    r'\btrap\b',
    r'\bcorner\b',
    r'\bblock\b',
    r'\bhood\b',
    r'\bghetto\b',
    r'\bproject\b',
    r'\bslum\b',
    r'\bstreet\b',
    r'\balley\b',
    r'\bunderground\b',
    r'\bblack\s+market\b',
    r'\billegal\b',
    r'\billicit\b',
    r'\bunlawful\b',
    r'\bcriminal\b',
    r'\bfelony\b',
    r'\bmisdemeanor\b',
    r'\barrest\b',
    r'\braid\b',
    r'\bbust\b',
    r'\bsting\b',
    r'\bnarc\b',
    r'\bcop\b',
    r'\bpolice\b',
    r'\bdea\b',
    r'\bfbi\b',
    r'\bfederal\b',
    r'\bagent\b',
    r'\binvestigation\b',
    r'\bsurveillance\b',
    r'\bwiretap\b',
    r'\binformant\b',
    r'\bsnitch\b',
    r'\brat\b',
    r'\bconfidential\b',
    r'\bundercover\b',
    r'\bsting\s+operation\b',
    r'\btask\s+force\b',
    r'\benforcement\b',
    r'\bprosecution\b',
    r'\bindictment\b',
    r'\bcharge\b',
    r'\bconviction\b',
    r'\bsentence\b',
    r'\bprison\b',
    r'\bjail\b',
    r'\bincarceration\b',
    r'\bprobation\b',
    r'\bparole\b',
    r'\brecord\b',
    r'\bbackground\s+check\b',
    r'\bcontrolled\s+substance\b',
    r'\bschedule\s+i\b',
    r'\bschedule\s+ii\b',
    r'\bschedule\s+iii\b',
    r'\bschedule\s+iv\b',
    r'\bschedule\s+v\b',
    r'\bscheduled\b',
    r'\bclassified\b',
    r'\brestricted\b',
    r'\bprohibited\b',
    r'\bbanned\b',
    r'\bforbidden\b',
    r'\bunauthorized\b',
    r'\bpossession\b',
    r'\bdistribution\b',
    r'\bmanufacturing\b',
    r'\btrafficking\b',
    r'\bsmuggling\b',
    r'\bimport\b',
    r'\bexport\b',
    r'\btransport\b',
    r'\bdeliver\b',
    r'\bsupply\b',
    r'\bintent\b',
    r'\bintended\b',
    r'\bpurpose\b',
    r'\bfor\s+sale\b',
    r'\bfor\s+profit\b',
    r'\bmoney\s+laundering\b',
    r'\bproceeds\b',
    r'\bcash\b',
    r'\buntraceable\b',
    r'\bcrypto\b',
    r'\bbitcoin\b',
    r'\bdark\s+web\b',
    r'\bdarknet\b',
    r'\btor\b',
    r'\bonion\b',
    r'\bsilk\s+road\b',
    r'\balphabay\b',
    r'\bhansa\b',
    r'\bdream\s+market\b',
    r'\bwall\s+street\b',
    r'\bempire\b',
    r'\bvalhalla\b',
    r'\bberlin\b',
    r'\btochka\b',
    r'\bcannazon\b',
    r'\bwhite\s+house\b',
    r'\bmonopoly\b',
    r'\bversus\b',
    r'\btorrez\b',
    r'\bcannahome\b',
    r'\bworld\s+market\b',
    r'\bescrow\b',
    r'\bvendor\b',
    r'\bmarket\b',
    r'\bmarketplace\b',
    r'\blisting\b',
    r'\bproduct\b',
    r'\bpackage\b',
    r'\bshipping\b',
    r'\bdelivery\b',
    r'\btracking\b',
    r'\bstealth\b',
    r'\bvacuum\s+sealed\b',
    r'\bmylar\b',
    r'\bdecoy\b',
    r'\bdisguise\b',
    r'\bhidden\b',
    r'\bconcealed\b',
    r'\bsmugglers?\b',
    r'\bmule\b',
    r'\bcourier\b',
    r'\bcarrier\b',
    r'\bswallow\b',
    r'\bbody\s+packing\b',
    r'\binternal\b',
    r'\bexternal\b',
    r'\bcavity\b',
    r'\brectal\b',
    r'\bvaginal\b',
    r'\bintestinal\b',
    r'\bdigestive\b',
    r'\bballoon\b',
    r'\bcondom\b',
    r'\bplastic\b',
    r'\bwrapped\b',
    r'\bsealed\b',
    r'\btaped\b',
    r'\bswallowed\b',
    r'\bingested\b',
    r'\binserted\b',
    r'\bplaced\b',
    r'\bhid\b',
    r'\bhidden\b',
    r'\bstashed\b',
    r'\bburied\b',
    r'\bplanted\b',
    r'\bleft\b',
    r'\bdropped\b',
    r'\bdead\s+drop\b',
    r'\bcache\b',
    r'\blocation\b',
    r'\bspot\b',
    r'\bplace\b',
    r'\bmeet\b',
    r'\brendezvous\b',
    r'\bpickup\b',
    r'\bdropoff\b',
    r'\bexchange\b',
    r'\btransaction\b',
    r'\bdeal\b',
    r'\bbusiness\b',
    r'\boperation\b',
    r'\bscheme\b',
    r'\bscam\b',
    r'\bfraud\b',
    r'\bdeceit\b',
    r'\bdeception\b',
    r'\blie\b',
    r'\bliar\b',
    r'\bcheat\b',
    r'\bcheater\b',
    r'\bthief\b',
    r'\bsteal\b',
    r'\bstole\b',
    r'\bstolen\b',
    r'\brob\b',
    r'\brobbed\b',
    r'\brobber\b',
    r'\bburgle\b',
    r'\bburglar\b',
    r'\bburglary\b',
    r'\bbreak-in\b',
    r'\bbreak\s+in\b',
    r'\bentry\b',
    r'\btrespass\b',
    r'\bintrude\b',
    r'\bintrusion\b',
    r'\binvade\b',
    r'\binvasion\b',
    r'\bviolate\b',
    r'\bviolation\b',
    r'\boffense\b',
    r'\bcrime\b',
    r'\bcriminal\b',
    r'\bgang\b',
    r'\bcartel\b',
    r'\bmafia\b',
    r'\bmob\b',
    r'\bsyndicate\b',
    r'\borganization\b',
    r'\bnetwork\b',
    r'\bring\b',
    r'\bcell\b',
    r'\bcrew\b',
    r'\bteam\b',
    r'\bgroup\b',
    r'\bfaction\b',
    r'\bsect\b',
    r'\bcult\b',
    r'\bextremist\b',
    r'\bradical\b',
    r'\bmilitant\b',
    r'\bterrorist\b',
    r'\bterrorism\b',
    r'\binsurgent\b',
    r'\bguerrilla\b',
    r'\brebel\b',
    r'\buprise\b',
    r'\brebellion\b',
    r'\brevolt\b',
    r'\brevolution\b',
    r'\boverthrow\b',
    r'\bcoup\b',
    r'\bassassinate\b',
    r'\bassassination\b',
    r'\bmurder\b',
    r'\bkill\b',
    r'\bkiller\b',
    r'\bhomicide\b',
    r'\bmanslaughter\b',
    r'\bdeath\b',
    r'\bdead\b',
    r'\bdie\b',
    r'\bdying\b',
    r'\bsuicide\b',
    r'\bself-harm\b',
    r'\bself\s+harm\b',
    r'\bharm\b',
    r'\bhurt\b',
    r'\binjure\b',
    r'\binjury\b',
    r'\bwound\b',
    r'\btrauma\b',
    r'\bdamage\b',
    r'\bdestroy\b',
    r'\bdestruction\b',
    r'\bdemolish\b',
    r'\bruin\b',
    r'\bwreck\b',
    r'\bsabotage\b',
    r'\bvandalise\b',
    r'\bvandalism\b',
    r'\bdeface\b',
    r'\bgraffiti\b',
    r'\btag\b',
    r'\bspray\s+paint\b',
    r'\bmarker\b',
    r'\bsticker\b',
    r'\bposter\b',
    r'\bflyer\b',
    r'\bpamphlet\b',
    r'\bleaflet\b',
    r'\bbrochure\b',
    r'\bhandout\b',
    r'\bdistribute\b',
    r'\bspread\b',
    r'\bpropagate\b',
    r'\bpromote\b',
    r'\badvocate\b',
    r'\bencourage\b',
    r'\bincite\b',
    r'\bprovoke\b',
    r'\binstigate\b',
    r'\binspire\b',
    r'\bmotivate\b',
    r'\bconvince\b',
    r'\bpersuade\b',
    r'\bcoerce\b',
    r'\bforce\b',
    r'\bcompel\b',
    r'\boblige\b',
    r'\brequire\b',
    r'\bdemand\b',
    r'\binsist\b',
    r'\bpressure\b',
    r'\bthreaten\b',
    r'\bthreat\b',
    r'\bintimidation\b',
    r'\bintimidate\b',
    r'\bbully\b',
    r'\bharass\b',
    r'\bharassment\b',
    r'\bstalk\b',
    r'\bstalker\b',
    r'\bstalking\b',
    r'\bfollow\b',
    r'\btrack\b',
    r'\bmonitor\b',
    r'\bwatch\b',
    r'\bobserve\b',
    r'\bspy\b',
    r'\bespionage\b',
    r'\bintelligence\b',
    r'\bcovert\b',
    r'\bclandestine\b',
    r'\bsecret\b',
    r'\bclassified\b',
    r'\bconfidential\b',
    r'\bprivate\b',
    r'\bhidden\b',
    r'\bconcealed\b',
    r'\bdisguised\b',
    r'\bcamouflaged\b',
    r'\bmasked\b',
    r'\bcover\b',
    r'\bfront\b',
    r'\bfacade\b',
    r'\bpretense\b',
    r'\bdeception\b',
    r'\btrick\b',
    r'\bhoax\b',
    r'\bfraud\b',
    r'\bfake\b',
    r'\bcounterfeit\b',
    r'\bforgery\b',
    r'\bforged\b',
    r'\bfalse\b',
    r'\buntrue\b',
    r'\bmisleading\b',
    r'\bmisinformation\b',
    r'\bdisinformation\b',
    r'\blie\b',
    r'\blies\b',
    r'\bfabrication\b',
    r'\binvention\b',
    r'\bmade\s+up\b',
    r'\bfictitious\b',
    r'\bimaginary\b',
    r'\bunreal\b',
    r'\bphony\b',
    r'\bbogus\b',
    r'\bsham\b',
    r'\bmockery\b',
    r'\bparody\b',
    r'\bsatire\b',
    r'\bcaricature\b',
    r'\bexaggeration\b',
    r'\bhyperbole\b',
    r'\boverstatement\b',
    r'\binflation\b',
    r'\bmagnification\b',
    r'\bamplification\b',
    r'\benhancement\b',
    r'\baugmentation\b',
    r'\bboost\b',
    r'\bincrease\b',
    r'\belevate\b',
    r'\braise\b',
    r'\blift\b',
    r'\buplift\b',
    r'\bimprove\b',
    r'\benhance\b',
    r'\bupgrade\b',
    r'\badvance\b',
    r'\bprogress\b',
    r'\bdevelop\b',
    r'\bgrow\b',
    r'\bexpand\b',
    r'\bextend\b',
    r'\benlarge\b',
    r'\bbroaden\b',
    r'\bwiden\b',
    r'\bspread\b',
    r'\bdisperse\b',
    r'\bscatter\b',
    r'\bdistribute\b',
    r'\bdispense\b',
    r'\ballot\b',
    r'\bdivide\b',
    r'\bsplit\b',
    r'\bseparate\b',
    r'\bpartition\b',
    r'\bsegment\b',
    r'\bsection\b',
    r'\bportion\b',
    r'\bfraction\b',
    r'\bpiece\b',
    r'\bpart\b',
    r'\bshare\b',
    r'\bcut\b',
    r'\bslice\b',
    r'\bchunk\b',
    r'\bblock\b',
    r'\bslab\b',
    r'\bbar\b',
    r'\bingot\b',
    r'\bbrick\b',
]


def contains_illegal_content(text):
    if not text or not isinstance(text, str):
        return False
    
    text_lower = text.lower()
    text_clean = re.sub(r'[^\w\s]', ' ', text_lower)
    
    for pattern in ILLEGAL_CONTENT_PATTERNS:
        if re.search(pattern, text_clean, re.IGNORECASE):
            return True
    
    return False


def is_safe_url(url):
    if not url or not isinstance(url, str):
        return True
    
    url_lower = url.lower()
    
    command_injection_patterns = [
        r';\s*curl',
        r';\s*wget',
        r';\s*bash',
        r';\s*sh\s',
        r';\s*cat\s',
        r';\s*rm\s',
        r';\s*chmod',
        r';\s*python',
        r';\s*perl',
        r';\s*node',
        r'\|\s*curl',
        r'\|\s*wget',
        r'\|\s*bash',
        r'&&\s*curl',
        r'&&\s*wget',
        r'\$\{IFS\}',
        r'\$IFS',
        r'`curl',
        r'`wget',
        r'`cat',
        r'\$\(curl',
        r'\$\(wget',
        r'\$\(cat',
        r'@\.env',
        r'\.env\s',
        r'\.config\s',
        r'/etc/passwd',
        r'/etc/shadow',
        r'file=@',
        r'-F\s+file',
        r'-X\s+POST',
        r'javascript:',
        r'<script',
        r'eval\(',
        r'exec\(',
        r'system\(',
        r'shell_exec',
        r'file://',
        r'%00',
        r'%0a',
        r'%0d',
    ]
    
    for pattern in command_injection_patterns:
        if re.search(pattern, url_lower, re.IGNORECASE):
            return False
    
    if url.count(';') > 0 or url.count('|') > 1:
        if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            url_parts = url.split('?', 1)
            if len(url_parts) > 1:
                params = url_parts[1]
                if ';' in params or '|' in params:
                    suspicious_after = params.split(';')[1] if ';' in params else params.split('|')[1]
                    if any(cmd in suspicious_after.lower() for cmd in ['curl', 'wget', 'bash', 'cat', 'env', 'file']):
                        return False
        else:
            return False
    
    allowed_domains = [
        'youtube.com',
        'youtu.be',
        'spotify.com',
        'apple.com',
        'music.apple.com',
        'soundcloud.com',
        'resso.com',
    ]
    
    if url.startswith('http://') or url.startswith('https://'):
        domain_match = re.search(r'https?://(?:www\.)?([^/?\s]+)', url)
        if domain_match:
            domain = domain_match.group(1).lower()
            is_allowed = any(allowed in domain for allowed in allowed_domains)
            if not is_allowed and not url.startswith('https://t.me/'):
                return False
    
    return True


def sanitize_query(query):
    if not query or not isinstance(query, str):
        return query
    
    query = query.strip()
    
    if contains_illegal_content(query):
        return None
    
    dangerous_patterns = [
        r';\s*curl',
        r';\s*wget',
        r';\s*bash',
        r'\|\s*curl',
        r'\$\{IFS\}',
        r'\.env',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            return None
    
    return query


@nand.on_message(
    filters.command(
        [
            "play",
            "vplay",
            "cplay",
            "cvplay",
            "playforce",
            "vplayforce",
            "cplayforce",
            "cvplayforce",
        ],
        prefixes=["", "/", "!", "%", ",", ".", "@", "#"]
    )
    & filters.group
    & ~BANNED_USERS
)
@PlayWrapper
async def play_commnd(
    client,
    message: Message,
    _,
    chat_id,
    video,
    channel,
    playmode,
    url,
    fplay,
):
    mystic = await message.reply_text(
        _["play_2"].format(channel) if channel else _["play_1"]
    )
    plist_id = None
    slider = None
    plist_type = None
    spotify = None
    user_id = message.from_user.id
    user_name = message.from_user.mention
    audio_telegram = (
        (message.reply_to_message.audio or message.reply_to_message.voice)
        if message.reply_to_message
        else None
    )
    video_telegram = (
        (message.reply_to_message.video or message.reply_to_message.document)
        if message.reply_to_message
        else None
    )
    
    if url:
        if not is_safe_url(url):
            return await mystic.edit_text(
                "⚠️ <b>Security Alert!</b>\n\n"
                "<b>Invalid or potentially harmful URL detected.</b>\n"
                "Only valid music platform URLs are allowed."
            )
        
        if contains_illegal_content(url):
            return await mystic.edit_text(
                "⚠️ <b>Content Blocked!</b>\n\n"
                "<b>This request contains illegal or prohibited content.</b>\n"
                "Please use appropriate search terms."
            )
    
    if audio_telegram:
        file_name_check = await Telegram.get_filename(audio_telegram, audio=True)
        if contains_illegal_content(file_name_check):
            return await mystic.edit_text(
                "⚠️ <b>Content Blocked!</b>\n\n"
                "<b>This file contains illegal or prohibited content.</b>"
            )
        
        if audio_telegram.file_size > 104857600:
            return await mystic.edit_text(_["play_5"])
        duration_min = seconds_to_min(audio_telegram.duration)
        if (audio_telegram.duration) > config.DURATION_LIMIT:
            return await mystic.edit_text(
                _["play_6"].format(config.DURATION_LIMIT_MIN, nand.mention)
            )
        file_path = await Telegram.get_filepath(audio=audio_telegram)
        if await Telegram.download(_, message, mystic, file_path):
            message_link = await Telegram.get_link(message)
            file_name = file_name_check
            dur = await Telegram.get_duration(audio_telegram, file_path)
            details = {
                "title": file_name,
                "link": message_link,
                "path": file_path,
                "dur": dur,
            }

            try:
                await stream(
                    _,
                    mystic,
                    user_id,
                    details,
                    chat_id,
                    user_name,
                    message.chat.id,
                    streamtype="telegram",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
                return await mystic.edit_text(err)
            return await mystic.delete()
        return
    elif video_telegram:
        file_name_check = await Telegram.get_filename(video_telegram)
        if contains_illegal_content(file_name_check):
            return await mystic.edit_text(
                "⚠️ <b>Content Blocked!</b>\n\n"
                "<b>This file contains illegal or prohibited content.</b>"
            )
        
        if message.reply_to_message.document:
            try:
                ext = video_telegram.file_name.split(".")[-1]
                if ext.lower() not in formats:
                    return await mystic.edit_text(
                        _["play_7"].format(f"{' | '.join(formats)}")
                    )
            except:
                return await mystic.edit_text(
                    _["play_7"].format(f"{' | '.join(formats)}")
                )
        if video_telegram.file_size > config.TG_VIDEO_FILESIZE_LIMIT:
            return await mystic.edit_text(_["play_8"])
        file_path = await Telegram.get_filepath(video=video_telegram)
        if await Telegram.download(_, message, mystic, file_path):
            message_link = await Telegram.get_link(message)
            file_name = file_name_check
            dur = await Telegram.get_duration(video_telegram, file_path)
            details = {
                "title": file_name,
                "link": message_link,
                "path": file_path,
                "dur": dur,
            }
            try:
                await stream(
                    _,
                    mystic,
                    user_id,
                    details,
                    chat_id,
                    user_name,
                    message.chat.id,
                    video=True,
                    streamtype="telegram",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
                return await mystic.edit_text(err)
            return await mystic.delete()
        return
    elif url:
        if await YouTube.exists(url):
            if "playlist" in url:
                try:
                    details = await YouTube.playlist(
                        url,
                        config.PLAYLIST_FETCH_LIMIT,
                        message.from_user.id,
                    )
                except:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "yt"
                if "&" in url:
                    plist_id = (url.split("=")[1]).split("&")[0]
                else:
                    plist_id = url.split("=")[1]
                img = config.PLAYLIST_IMG_URL
                cap = _["play_9"]
            else:
                try:
                    details, track_id = await YouTube.track(url)
                except:
                    return await mystic.edit_text(_["play_3"])
                
                if contains_illegal_content(details.get("title", "")):
                    return await mystic.edit_text(
                        "⚠️ <b>Content Blocked!</b>\n\n"
                        "<b>This video contains illegal or prohibited content.</b>"
                    )
                
                streamtype = "youtube"
                img = details["thumb"]
                cap = _["play_10"].format(
                    details["title"],
                    details["duration_min"],
                )
        elif await Spotify.valid(url):
            spotify = True
            if not config.SPOTIFY_CLIENT_ID and not config.SPOTIFY_CLIENT_SECRET:
                return await mystic.edit_text(
                    "» sᴘᴏᴛɪғʏ ɪs ɴᴏᴛ sᴜᴘᴘᴏʀᴛᴇᴅ ʏᴇᴛ.\n\nᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ."
                )
            if "track" in url:
                try:
                    details, track_id = await Spotify.track(url)
                except:
                    return await mystic.edit_text(_["play_3"])
                
                if contains_illegal_content(details.get("title", "")):
                    return await mystic.edit_text(
                        "⚠️ <b>Content Blocked!</b>\n\n"
                        "<b>This track contains illegal or prohibited content.</b>"
                    )
                
                streamtype = "youtube"
                img = details["thumb"]
                cap = _["play_10"].format(details["title"], details["duration_min"])
            elif "playlist" in url:
                try:
                    details, plist_id = await Spotify.playlist(url)
                except Exception:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "spplay"
                img = config.SPOTIFY_PLAYLIST_IMG_URL
                cap = _["play_11"].format(nand.mention, message.from_user.mention)
            elif "album" in url:
                try:
                    details, plist_id = await Spotify.album(url)
                except:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "spalbum"
                img = config.SPOTIFY_ALBUM_IMG_URL
                cap = _["play_11"].format(nand.mention, message.from_user.mention)
            elif "artist" in url:
                try:
                    details, plist_id = await Spotify.artist(url)
                except:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "spartist"
                img = config.SPOTIFY_ARTIST_IMG_URL
                cap = _["play_11"].format(message.from_user.first_name)
            else:
                return await mystic.edit_text(_["play_15"])
        elif await Apple.valid(url):
            if "album" in url:
                try:
                    details, track_id = await Apple.track(url)
                except:
                    return await mystic.edit_text(_["play_3"])
                
                if contains_illegal_content(details.get("title", "")):
                    return await mystic.edit_text(
                        "⚠️ <b>Content Blocked!</b>\n\n"
                        "<b>This track contains illegal or prohibited content.</b>"
                    )
                
                streamtype = "youtube"
                img = details["thumb"]
                cap = _["play_10"].format(details["title"], details["duration_min"])
            elif "playlist" in url:
                spotify = True
                try:
                    details, plist_id = await Apple.playlist(url)
                except:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "apple"
                cap = _["play_12"].format(nand.mention, message.from_user.mention)
                img = url
            else:
                return await mystic.edit_text(_["play_3"])
        elif await Resso.valid(url):
            try:
                details, track_id = await Resso.track(url)
            except:
                return await mystic.edit_text(_["play_3"])
            
            if contains_illegal_content(details.get("title", "")):
                return await mystic.edit_text(
                    "⚠️ <b>Content Blocked!</b>\n\n"
                    "<b>This track contains illegal or prohibited content.</b>"
                )
            
            streamtype = "youtube"
            img = details["thumb"]
            cap = _["play_10"].format(details["title"], details["duration_min"])
        elif await SoundCloud.valid(url):
            try:
                details, track_path = await SoundCloud.download(url)
            except:
                return await mystic.edit_text(_["play_3"])
            
            if contains_illegal_content(details.get("title", "")):
                return await mystic.edit_text(
                    "⚠️ <b>Content Blocked!</b>\n\n"
                    "<b>This track contains illegal or prohibited content.</b>"
                )
            
            duration_sec = details["duration_sec"]
            if duration_sec > config.DURATION_LIMIT:
                return await mystic.edit_text(
                    _["play_6"].format(
                        config.DURATION_LIMIT_MIN,
                        nand.mention,
                    )
                )
            try:
                await stream(
                    _,
                    mystic,
                    user_id,
                    details,
                    chat_id,
                    user_name,
                    message.chat.id,
                    streamtype="soundcloud",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
                return await mystic.edit_text(err)
            return await mystic.delete()
        else:
            try:
                await Shruti.stream_call(url)
            except NoActiveGroupCall:
                await mystic.edit_text(_["black_9"])
                return await nand.send_message(
                    chat_id=config.LOGGER_ID,
                    text=_["play_17"],
                )
            except Exception as e:
                return await mystic.edit_text(_["general_2"].format(type(e).__name__))
            await mystic.edit_text(_["str_2"])
            try:
                await stream(
                    _,
                    mystic,
                    message.from_user.id,
                    url,
                    chat_id,
                    message.from_user.first_name,
                    message.chat.id,
                    video=video,
                    streamtype="index",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
                return await mystic.edit_text(err)
            return await play_logs(message, streamtype="M3u8 or Index Link")
    else:
        if len(message.command) < 2:
            buttons = botplaylist_markup(_)
            return await mystic.edit_text(
                _["play_18"],
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        slider = True
        query = message.text.split(None, 1)[1]
        
        sanitized_query = sanitize_query(query)
        if sanitized_query is None:
            return await mystic.edit_text(
                "⚠️ <b>Content Blocked!</b>\n\n"
                "<b>This request contains illegal or prohibited content.</b>\n"
                "Please use appropriate search terms."
            )
        query = sanitized_query
        
        if "-v" in query:
            query = query.replace("-v", "")
        try:
            details, track_id = await YouTube.track(query)
        except:
            return await mystic.edit_text(_["play_3"])
        
        if contains_illegal_content(details.get("title", "")):
            return await mystic.edit_text(
                "⚠️ <b>Content Blocked!</b>\n\n"
                "<b>This search result contains illegal or prohibited content.</b>"
            )
        
        streamtype = "youtube"
    if str(playmode) == "Direct":
        if not plist_type:
            if details["duration_min"]:
                duration_sec = time_to_seconds(details["duration_min"])
                if duration_sec > config.DURATION_LIMIT:
                    return await mystic.edit_text(
                        _["play_6"].format(config.DURATION_LIMIT_MIN, nand.mention)
                    )
            else:
                buttons = livestream_markup(
                    _,
                    track_id,
                    user_id,
                    "v" if video else "a",
                    "c" if channel else "g",
                    "f" if fplay else "d",
                )
                return await mystic.edit_text(
                    _["play_13"],
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
        try:
            await stream(
                _,
                mystic,
                user_id,
                details,
                chat_id,
                user_name,
                message.chat.id,
                video=video,
                streamtype=streamtype,
                spotify=spotify,
                forceplay=fplay,
            )
        except Exception as e:
            ex_type = type(e).__name__
            err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
            return await mystic.edit_text(err)
        await mystic.delete()
        return await play_logs(message, streamtype=streamtype)
    else:
        if plist_type:
            ran_hash = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=10)
            )
            lyrical[ran_hash] = plist_id
            buttons = playlist_markup(
                _,
                ran_hash,
                message.from_user.id,
                plist_type,
                "c" if channel else "g",
                "f" if fplay else "d",
            )
            await mystic.delete()
            await message.reply_photo(
                photo=img,
                caption=cap,
                reply_markup=InlineKeyboardMarkup(buttons),
            )
            return await play_logs(message, streamtype=f"Playlist : {plist_type}")
        else:
            if slider:
                buttons = slider_markup(
                    _,
                    track_id,
                    message.from_user.id,
                    query,
                    0,
                    "c" if channel else "g",
                    "f" if fplay else "d",
                )
                await mystic.delete()
                await message.reply_photo(
                    photo=details["thumb"],
                    caption=_["play_10"].format(
                        details["title"].title(),
                        details["duration_min"],
                    ),
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
                return await play_logs(message, streamtype=f"Searched on Youtube")
            else:
                buttons = track_markup(
                    _,
                    track_id,
                    message.from_user.id,
                    "c" if channel else "g",
                    "f" if fplay else "d",
                )
                await mystic.delete()
                await message.reply_photo(
                    photo=img,
                    caption=cap,
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
                return await play_logs(message, streamtype=f"URL Searched Inline")


@nand.on_callback_query(filters.regex("MusicStream") & ~BANNED_USERS)
@languageCB
async def play_music(client, CallbackQuery, _):
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    vidid, user_id, mode, cplay, fplay = callback_request.split("|")
    if CallbackQuery.from_user.id != int(user_id):
        try:
            return await CallbackQuery.answer(_["playcb_1"], show_alert=True)
        except:
            return
    try:
        chat_id, channel = await get_channeplayCB(_, cplay, CallbackQuery)
    except:
        return
    user_name = CallbackQuery.from_user.first_name
    try:
        await CallbackQuery.message.delete()
        await CallbackQuery.answer()
    except:
        pass
    mystic = await CallbackQuery.message.reply_text(
        _["play_2"].format(channel) if channel else _["play_1"]
    )
    try:
        details, track_id = await YouTube.track(vidid, True)
    except:
        return await mystic.edit_text(_["play_3"])
    
    if contains_illegal_content(details.get("title", "")):
        return await mystic.edit_text(
            "⚠️ <b>Content Blocked!</b>\n\n"
            "<b>This video contains illegal or prohibited content.</b>"
        )
    
    if details["duration_min"]:
        duration_sec = time_to_seconds(details["duration_min"])
        if duration_sec > config.DURATION_LIMIT:
            return await mystic.edit_text(
                _["play_6"].format(config.DURATION_LIMIT_MIN, nand.mention)
            )
    else:
        buttons = livestream_markup(
            _,
            track_id,
            CallbackQuery.from_user.id,
            mode,
            "c" if cplay == "c" else "g",
            "f" if fplay else "d",
        )
        return await mystic.edit_text(
            _["play_13"],
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    video = True if mode == "v" else None
    ffplay = True if fplay == "f" else None
    try:
        await stream(
            _,
            mystic,
            CallbackQuery.from_user.id,
            details,
            chat_id,
            user_name,
            CallbackQuery.message.chat.id,
            video,
            streamtype="youtube",
            forceplay=ffplay,
        )
    except Exception as e:
        ex_type = type(e).__name__
        err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
        return await mystic.edit_text(err)
    return await mystic.delete()


@nand.on_callback_query(filters.regex("ShrutimousAdmin") & ~BANNED_USERS)
async def Shrutimous_check(client, CallbackQuery):
    try:
        await CallbackQuery.answer(
            "» ʀᴇᴠᴇʀᴛ ʙᴀᴄᴋ ᴛᴏ ᴜsᴇʀ ᴀᴄᴄᴏᴜɴᴛ :\n\nᴏᴘᴇɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ sᴇᴛᴛɪɴɢs.\n-> ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs\n-> ᴄʟɪᴄᴋ ᴏɴ ʏᴏᴜʀ ɴᴀᴍᴇ\n-> ᴜɴᴄʜᴇᴄᴋ ᴀɴᴏɴʏᴍᴏᴜs ᴀᴅᴍɪɴ ᴘᴇʀᴍɪssɪᴏɴs.",
            show_alert=True,
        )
    except:
        pass


@nand.on_callback_query(filters.regex("ShrutiPlaylists") & ~BANNED_USERS)
@languageCB
async def play_playlists_command(client, CallbackQuery, _):
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    (
        videoid,
        user_id,
        ptype,
        mode,
        cplay,
        fplay,
    ) = callback_request.split("|")
    if CallbackQuery.from_user.id != int(user_id):
        try:
            return await CallbackQuery.answer(_["playcb_1"], show_alert=True)
        except:
            return
    try:
        chat_id, channel = await get_channeplayCB(_, cplay, CallbackQuery)
    except:
        return
    user_name = CallbackQuery.from_user.first_name
    await CallbackQuery.message.delete()
    try:
        await CallbackQuery.answer()
    except:
        pass
    mystic = await CallbackQuery.message.reply_text(
        _["play_2"].format(channel) if channel else _["play_1"]
    )
    videoid = lyrical.get(videoid)
    video = True if mode == "v" else None
    ffplay = True if fplay == "f" else None
    spotify = True
    if ptype == "yt":
        spotify = False
        try:
            result = await YouTube.playlist(
                videoid,
                config.PLAYLIST_FETCH_LIMIT,
                CallbackQuery.from_user.id,
                True,
            )
        except:
            return await mystic.edit_text(_["play_3"])
    if ptype == "spplay":
        try:
            result, spotify_id = await Spotify.playlist(videoid)
        except:
            return await mystic.edit_text(_["play_3"])
    if ptype == "spalbum":
        try:
            result, spotify_id = await Spotify.album(videoid)
        except:
            return await mystic.edit_text(_["play_3"])
    if ptype == "spartist":
        try:
            result, spotify_id = await Spotify.artist(videoid)
        except:
            return await mystic.edit_text(_["play_3"])
    if ptype == "apple":
        try:
            result, apple_id = await Apple.playlist(videoid, True)
        except:
            return await mystic.edit_text(_["play_3"])
    try:
        await stream(
            _,
            mystic,
            user_id,
            result,
            chat_id,
            user_name,
            CallbackQuery.message.chat.id,
            video,
            streamtype="playlist",
            spotify=spotify,
            forceplay=ffplay,
        )
    except Exception as e:
        ex_type = type(e).__name__
        err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
        return await mystic.edit_text(err)
    return await mystic.delete()


@nand.on_callback_query(filters.regex("slider") & ~BANNED_USERS)
@languageCB
async def slider_queries(client, CallbackQuery, _):
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    (
        what,
        rtype,
        query,
        user_id,
        cplay,
        fplay,
    ) = callback_request.split("|")
    if CallbackQuery.from_user.id != int(user_id):
        try:
            return await CallbackQuery.answer(_["playcb_1"], show_alert=True)
        except:
            return
    what = str(what)
    rtype = int(rtype)
    if what == "F":
        if rtype == 9:
            query_type = 0
        else:
            query_type = int(rtype + 1)
        try:
            await CallbackQuery.answer(_["playcb_2"])
        except:
            pass
        title, duration_min, thumbnail, vidid = await YouTube.slider(query, query_type)
        
        if contains_illegal_content(title):
            try:
                await CallbackQuery.answer(
                    "⚠️ Content blocked - contains prohibited terms",
                    show_alert=True
                )
            except:
                pass
            return
        
        buttons = slider_markup(_, vidid, user_id, query, query_type, cplay, fplay)
        med = InputMediaPhoto(
            media=thumbnail,
            caption=_["play_10"].format(
                title.title(),
                duration_min,
            ),
        )
        return await CallbackQuery.edit_message_media(
            media=med, reply_markup=InlineKeyboardMarkup(buttons)
        )
    if what == "B":
        if rtype == 0:
            query_type = 9
        else:
            query_type = int(rtype - 1)
        try:
            await CallbackQuery.answer(_["playcb_2"])
        except:
            pass
        title, duration_min, thumbnail, vidid = await YouTube.slider(query, query_type)
        
        if contains_illegal_content(title):
            try:
                await CallbackQuery.answer(
                    "⚠️ Content blocked - contains prohibited terms",
                    show_alert=True
                )
            except:
                pass
            return
        
        buttons = slider_markup(_, vidid, user_id, query, query_type, cplay, fplay)
        med = InputMediaPhoto(
            media=thumbnail,
            caption=_["play_10"].format(
                title.title(),
                duration_min,
            ),
        )
        return await CallbackQuery.edit_message_media(
            media=med, reply_markup=InlineKeyboardMarkup(buttons)
        )
