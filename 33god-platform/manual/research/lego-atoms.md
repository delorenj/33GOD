# LEGO instruction atoms: design research for I-10 The Manual

Researched 2026-11-11. Scope: what LEGO's instruction grammar is made of, why a wordless
picture manual works on a reader who will not read, and which tricks other traditions add.
This is research only. It proposes no grammar. Mapping seeds are labelled hypotheses for the
grammar-design task that follows.

Evidence tags used throughout:

- **[P]** read in full or near-full from the primary document (LEGO, FAA report, journal PDFs).
- **[S]** read from a secondary page (fan site, blog, encyclopedia).
- **[Snip]** seen only in a search-result snippet. Treat as a lead, not a fact.
- **[Inf]** my inference. Not in any source.

Source numbers `[n]` point to the ledger in section 7.

---

## 0. The seven findings that matter most

1. **LEGO shows how, never why. The Manual must show both.** A LEGO page answers "what goes
   where next". The Manual's stated outcome is a mental model ("why an event system on NATS
   JetStream + Dapr"). A rule of thumb for graphic instructions (Coskuntuna & Mauro 1980,
   as reviewed in the FAA report) is "focus on actions, not reasons" [27], which is also
   what a LEGO page does [Inf]. So LEGO supplies no atom for *why*, and one has to be
   invented or borrowed (Lin Clark's analogy-first cartoons [37], Phippy [38], Beck's
   what-connects-to-what map [39]).

2. **LEGO gets away with "structural" diagrams because every brick connects the same way.**
   Agrawala et al. say it "may be less important" to show attachment operations in LEGO
   instructions "because most LEGO parts fasten in the same way". Their experiments found
   *action* diagrams (new parts pulled apart, with guide lines and arrows showing the
   attachment) superior to structural ones for a TV stand, whose parts fasten with
   different hardware [17]. Software components do not all attach the same way. The Manual
   therefore needs either (a) one universal "stud" that every connection uses, if the
   architecture truly has one, or (b) a small fixed set of **typed connectors**, each with
   its own arrow/line style. This is the biggest structural gap between LEGO and software.
   [P][Inf]

3. **Unfamiliar referents defeat pictures; familiar conventions survive.** In the FAA's
   785-person study, comprehension of briefing-card pictograms averaged 65% (range
   28.8-96.3%). Only 8.3% of item scores cleared the 85% ANSI bar. The four ANSI symbols people meet daily
   all scored over 90%, and comprehension tracked familiarity with the *thing depicted* [27].
   BrickNerd's kid test agrees. Only the rotate arrow and the green check/red X were
   understood by all three kids. The 1:1 scale, "piece not in bag", glow-in-the-dark and
   multi-builder symbols were not [6]. LEGO's builder can see the real bricks in the box, so
   the referent is never unfamiliar. A software reader has never seen a JetStream. The
   Manual needs an **analogy bridge** for every new referent, and it must reuse
   conventions Damian already knows.

4. **The correct acceptance test is a tell-back, and "wrong" must score worse than
   "incomplete".** Jentsch (1996), reviewed in the FAA report, scored each answer as
   complete-and-correct, incomplete-but-safe, or wrong-or-unsafe [27]. The FAA report calls
   open-ended responses "the gold standard of cognitive comprehension testing" [27]. This
   matches I-10's rule "Damian tells it back correctly after one read", and it fits
   "accurate, not a simplified false model". One reader is not
   a validated test population (the FAA used 785). Treat Damian as a fast, cheap first
   gate, not as proof.

5. **The scale bar is not a nesting meter in LEGO. The nesting atom is the submodel callout.**
   The 1:1 bar is a calibration to physical reality ("hold the real part against the
   picture"), paired with a circled stud count. Both are dual-coded, analog plus numeral
   [5][6]. The native LEGO device for hierarchy is the **submodel/callout box**. A Studio
   how-to guide says submodels can nest 3-4 deep (Steam engine > Boiler > Chimney) [14]. Jarad's
   nesting-meter idea can work, but three research results constrain it (see 2.8):
   people encode lengths in gross categories (Tversky [18]), working memory holds about 4
   chunks (Cowan [23]), and Isotype says to repeat units rather than resize them [30].
   Use a few discrete notches, not proportional lengths.

6. **Accuracy lives in congruence.** Tversky's Congruence Principle: "the structure and
   content of the external representation should correspond to the desired structure and
   content of the internal representation" [18]. For the Manual, the *drawn structure must
   be the real architecture's structure*, so the model the reader builds from the picture
   is the correct model. Beck's 1931 Tube map is the proof of method. It threw away
   geography and kept topology, and it is accurate about the only thing a rider needs [39].

7. **The 2022 LEGO "redesign" was packaging, not pedagogy.** See section 1.

---

## 1. Corrections to the task's premises

The task text and the vision doc carry a few claims that the evidence does not support. Code
and sources win over recollection.

| Premise | What the evidence says |
|---|---|
| New-part outlines/highlights "since 2022" | Highlighting new bricks is old. A 1988 set (6054) already outlined current-step black bricks in a subtle white outline and showed placed bricks dark grey [7]. Red outlines on newly placed pieces were already in use by 2021, and readers said losing them made manuals "noticeably harder to follow" (Brickset comments, 1 Mar 2021 [9]). Step-specific parts callouts date from 2003 (set 7470) [7]. |
| LEGO's 2022 "instruction redesign statement" | The only official statement found is a packaging/sustainability line: "The LEGO Group is on a journey to make its packaging more sustainable by 2025... other in-box materials such as the cover of Building Instructions have also been re-designed for a visually consistent unboxing experience" [10]. Covers went white/tan with outlined elements. Trade press says the page content "remain[s] functionally unchanged" [11]. There is **no** LEGO statement that the 2022 change was a cognitive redesign. |
| LEGO instruction history is one timeline | Sources disagree on dates. BrickNerd says Panther software ran from 1982 [7]. LEGO's own history page says the Panter tool ran 1986-2003 [4]. LEGO's page also confirms a specialist instruction team formed in **1983** [4]. |
| "The wordless constraint" is LEGO doctrine | I found no LEGO quote stating why instructions are wordless. The reasons (language independence, one print run worldwide) come from third parties about LEGO and IKEA [28][Snip]. Gizmodo's LEGO audio/braille piece quotes no LEGO rationale either [15]. Say "wordless works", not "LEGO says wordless because...". |

---

## 2. The LEGO atoms

Each atom gives: what it looks like, its cognitive job, rules for use, and a mapping seed.
Mapping seeds are hypotheses [Inf] to feed the grammar task. Jarad said not to take his
examples literally, so none of them is a decision.

### 2.1 Step number

- **Looks like:** a big numeral at the top-left of each step panel. Numbering restarts inside
  each submodel (Studio copies this LEGO convention [13]).
- **Cognitive job:** removes the "what do I do next" decision entirely. The reader follows a
  linear path and keeps a place. It is the anchor for the segmenting principle (learner-paced
  chunks [20]).
- **Rules:**
  - One number, one action-chunk.
  - Numbers are sequential and never skipped.
  - Restart numbering in a nested sub-build and return to the parent count afterwards [13].
  - Steps got *smaller* over time. Set 6054 (1988) had 23 steps in 16 pages. Set 40567 (2022)
    had 52 steps in 67 pages for a comparable build [7]. Single-brick steps now appear even
    in adult sets [8].
- **Mapping seed:** the page number is the step number. One page, one idea. Nested
  explanations restart the count.
- **Evidence:** [4][7][8][13] [S]

### 2.2 Parts-per-step callout box ("what you need for this step")

- **Looks like:** a framed box in a corner of the step panel showing the exact parts for
  *this* step, with a quantity (`2x`, `4x`). Step-specific boxes began in 2003 [7].
- **Cognitive job:** pre-training in miniature. It teaches the names and shapes of the pieces
  immediately before they are used (Mayer: learners "have learned the names and
  characteristics of the main concepts" [20]). It replaces "spot the difference" part-hunting
  with matching [8]. The box sits next to the action, which satisfies spatial contiguity [20].
- **Rules:**
  - The box lists only what the step uses.
  - It sits in a consistent corner.
  - Stud.io lets you move it if it blocks the picture [14].
  - It carries the quantity, so the drawing does not repeat the part five times.
- **Mapping seed:** a per-page "actors in this scene" box, listing the 1-4 components the
  page is about, drawn exactly as they were introduced on the legend page.
- **Evidence:** [7][8][14] [S]

### 2.3 New-part highlight and dimmed history

- **Looks like:** the parts added in this step are outlined (red in current booklets; subtle
  white on black bricks in the 1988 style). Earlier parts are shown plainer, in dark grey
  with black outlines in older booklets [7][9]. Studio's rendition is current step in normal
  colour, earlier steps as transparent wireframe, future steps hidden [14].
- **Cognitive job:** this is **signaling** (Mayer d=0.69 per a secondary summary [21], and
  "cues that highlight the organization of essential material" [20]). It answers "what
  changed since the last panel" without reading. The Agrawala rule backs it: new parts must
  be visible, earlier parts shown for context, and the new parts must not hide parts that
  come later [17]. Earl of Bricks calls highlighting "the single most important visual cue in
  any LEGO instruction set" [13] [S, opinion].
- **Rules:**
  - Exactly one highlight style, used for exactly one meaning.
  - The highlight colour must contrast with every colour in the model [13].
  - If you cannot tell what changed, **move the camera, do not add words** [13].
  - Old LEGO pages used black backgrounds. LEGO moved away from them after complaints that
    dark bricks vanished into them [9]. Background is not neutral.
- **Mapping seed:** one reserved colour for "new on this page". Everything already
  introduced is drawn muted. Never reuse the highlight colour for anything else.
- **Evidence:** [7][9][13][14][17][20] [S/P]

### 2.4 Submodel / sub-assembly callout

- **Looks like:** a separate small assembly built in its own framed box (or its own sequence
  of steps), then shown being attached to the main model. Boxes are for small sub-builds.
  Earl of Bricks: callouts suit sub-assemblies under five parts, and a sub-assembly with
  five or more internal steps gets its own sequence [13].
- **Cognitive job:** this is the **hierarchy atom**. Agrawala's experiments found people hold
  assemblies as a hierarchy of sub-assemblies, and "work down the subassembly hierarchy" [17].
  The callout lets the reader keep the parent in view while a child is built. It is the
  closest native LEGO device to Jarad's nesting idea.
- **Rules:**
  - Callout the sub-build when it is small (a Rebrickable/Studio search result says callouts
    are typically for submodels of 3 or fewer steps [Snip, not fetched]; the Studio guide
    says to reserve callouts for smaller submodels [14]).
  - Give it its own sequence when it is large.
  - Show where it plugs in.
  - Nest at most 3-4 levels (the Studio guide's example is Steam engine > Boiler > Chimney [14]).
    This agrees with Cowan's working-memory limit of about four chunks [23][Snip].
  - A two-level hierarchy (significant parts plus small fasteners) is enough for most
    objects [17].
- **Mapping seed:** the platform page shows "HeyMa" as a box; zooming into it is a callout
  page; inside that, wax/vinyl/phonograph, and so on. Names are Jarad's example from
  THE_MANUAL.md and were **not verified against live code** [1].
- **Evidence:** [13][14][17] [S/P]

### 2.5 Multiplier ("2x", "4x")

- **Looks like:** a small `2x` beside a submodel or part. For submodels, two identical copies
  built in the same step collapse to one picture plus `2x` (Stud.io reproduces this: two
  clones in the same step display as "x2") [Snip: Stud.io search result; Eurobricks thread
  not read].
- **Cognitive job:** compresses repetition. Agrawala found people find repeated operations
  tedious and recommend showing them in full a few times and skipping the rest. Their system's
  default is two full showings [17].
- **Rules:**
  - Show the pattern in full twice (Agrawala's default), then use the multiplier.
  - Use it only for truly identical items.
  - Never let the multiplier hide an exception.
- **Mapping seed:** "N copies of the same shape" for any fleet of look-alike components.
  Show the first two, then `xN`.
- **Evidence:** [17] [P]; Stud.io behaviour [Snip]

### 2.6 Rotate / flip arrow

- **Looks like:** a curved arrow beside the step picture, showing the model turned over or
  around before the next step. Stud.io can insert it automatically on a view change and puts
  it at page edges [14].
- **Cognitive job:** keeps the reader's mental model and the camera in sync. Orientation is a
  principle in Agrawala (most objects have natural preferred views; reorient only to keep new
  parts visible [17]). **It is the best-understood LEGO symbol in the kid test:** all three
  children read it correctly, and BrickNerd inducted it into the "symbol hall of fame" [6].
- **Rules:**
  - Use the arrow only when the camera changes.
  - Keep one canonical viewpoint otherwise.
  - Never rotate without the arrow.
- **Mapping seed:** a "change of viewpoint" mark whenever a page switches between, say, a
  box-and-arrow view and a "zoom into one box" view. The reader should never wonder whether
  the page is the same world seen differently.
- **Evidence:** [6][14][17] [S/P]

### 2.7 The 1:1 scale bar and circled length number

- **Looks like:** on pages where parts are hard to tell apart (Technic axles), the part is
  drawn at real size with a "1:1" bar, and a number in a circle gives its length in studs
  [5][6].
- **Cognitive job:** a **calibration to reality**. The reader holds the real piece against the
  picture. The circled number is a second code (digital beside analog) for the same fact. It
  is used only where shape alone cannot discriminate.
- **Rules (LEGO practice):**
  - Only appears when needed.
  - Analog and numeral together.
  - The kid test found it **confusing to younger kids** and understood mainly by experienced
    builders [6]. It is a taught symbol, not a guessable one.
- **Mapping seed, and caution:** the nesting-level reading is Jarad's invention, not a LEGO
  usage. If kept, design it from the evidence on perception (see 2.8 and finding 5): discrete
  notches, at most ~4 levels, a numeral as well as a bar, taught on page one. A second,
  closer mapping to the *actual* LEGO job is a "check this against the real box" ribbon: the
  page gives the reader a one-line way to see the claim live on their own machine. That would
  serve the I-10 rule that every drawn claim traces to live code. Both are hypotheses [Inf].
- **Evidence:** [5][6] [S]

### 2.8 Why a nesting meter must be coarse (supporting evidence)

- Tversky et al.: "people represent angles and lengths in gross categories, so finer
  distinctions in diagrams will not be accurately apprehended" [18] [P].
- Cowan: working memory holds about 4 chunks on average [23] [Snip].
- Isotype's first rule: to show more, repeat a same-size unit, do not enlarge the unit [30]
  [S].
- Together these say a nesting bar should be built from **countable same-size segments**
  (levels), not from a proportionally shrinking length that the eye must compare.
  [Inf, from sourced principles]

### 2.9 Numbered bags and the bag-start page

- **Looks like:** a bag icon with a numeral at the start of each build phase. The first
  numbered-bag sets were 2003-2005 (10123 Cloud City is cited for 2003; 4757 Hogwarts Castle
  2004; 8421 Mobile Crane 2005); wide adoption came about 2006-2007 [7][Snip].
- **Cognitive job:** physical **segmenting** and a natural pause. Brickset notes it cuts part
  hunting and lets younger sets be more complex [8]. UXmatters adds an overview page showing
  the sequence (open bags, build a section, next bag) so builders "organize their workspace
  and thoughts before they invest their time" [12].
- **Rules:**
  - Each bag is a complete, finishable chunk.
  - A visible "you finished a phase" moment follows.
  - An overview page precedes the first step.
- **Mapping seed:** a **chapter** = one concept cluster. A short "how to read this booklet"
  opener, then chapters of 3-6 pages, each ending on a "you built X" picture.
- **Evidence:** [7][8][12] [S]

### 2.10 The "+" (not-in-this-bag) symbol

- **Looks like:** a plus sign marking a part that is not in the current numbered bag
  (loose in the box or in an unnumbered bag) [5].
- **Cognitive job:** prevents a false "my part is missing" alarm. It marks "this comes from
  elsewhere".
- **Rules:** keep it rare, and place it exactly where the out-of-bag part enters. **Weak
  symbol in the kid test:** "pretty confusing" and it "definitely threw the panel for a
  loop" [6].
- **Mapping seed:** an "imported from outside this page" mark for something this page uses but
  does not own. It needs teaching, because this is exactly the kind of symbol novices miss.
- **Evidence:** [5][6] [S]

### 2.11 Multi-builder symbol

- **Looks like:** figures plus a count, showing how many people can build at once. Large sets
  ship several booklets so people can build in parallel [5].
- **Cognitive job:** it states that sections are independent. It is a statement about
  **dependency structure**.
- **Rules:** use only when the sections really are independent. This symbol was one of the
  poorly-understood ones in the kid test [6].
- **Mapping seed:** a "these parts run independently of each other" badge. Possibly useful for
  event-driven consumers that do not wait on one another. Verify against live behaviour first.
- **Evidence:** [5][6] [S]

### 2.12 Correct-orientation frame (green check / red X)

- **Looks like:** two small pictures, the right way marked with a green check and the wrong
  way with a red X, used when a part is easy to place backwards [6].
- **Cognitive job:** **error prevention by showing the wrong answer**. It exploits a
  universal convention. **Perfect comprehension in the kid test** (all three children) [6].
  IKEA does the same: "the part, the orientation, the intended result, the wrong result"
  [29][S], and a cross over a picture is its universal "don't" [Snip].
- **Rules:**
  - Show the wrong version only where mistakes are common.
  - Never show a wrong picture without the X.
  - Reuse check/X exactly as the world already uses them.
- **Mapping seed:** a "common wrong mental model" frame. For example, "it is NOT a pipe the
  message flows through". It pairs a false picture (X) with the true one (check). This is
  the best available atom for the I-10 rule "accurate, not simplified false". [Inf]
- **Evidence:** [6][29] [S]

### 2.13 Sticker icon

- **Looks like:** a small sheet graphic with a number that maps to a numbered sticker [5].
- **Cognitive job:** a lookup key between two physical things with a single number.
- **Rules:** the kid test was **mixed**; only the oldest child grasped the numbering [6].
- **Mapping seed:** low priority. Possibly "a label to apply" if the Manual ever gets
  overlay badges. No clear software meaning.
- **Evidence:** [5][6] [S]

### 2.14 Warning symbols (projectile, light-brick tag)

- **Looks like:** a prohibition mark (projectile: do not fire at eyes) and a "remove the
  battery tag" reminder [5].
- **Cognitive job:** hazard and one-time-setup flags.
- **Rules:** the projectile symbol conveyed "don't" but not *why* in the kid test [6].
  Hazards need a concrete picture of the harm, not only a prohibition.
- **Mapping seed:** a "hazard" atom for real foot-guns and a "one-time setup" atom. The
  grammar task must draw hazards from the live system, not from recollection or docs.
- **Evidence:** [5][6] [S]

### 2.15 Inventory pages

- **Looks like:** a parts list at the back (since about 2006), each element with its ID and
  quantity, often with the 1:1 view for similar parts [Snip: Brickset/Rebrickable results].
- **Cognitive job:** a **legend and a completeness check**. Studio's guide calls it "the map
  that tells the builder what to buy" [13].
- **Rules:** a complete, standard list; one name per part, everywhere.
- **Mapping seed:** the "meet the parts" legend. Mayer's **pre-training** principle says to
  teach the names and characteristics of the main concepts first, and it measures d=0.78
  per a secondary summary [20][21]. Put it **first**, not at the back, for a reader who may
  not turn to page 40. [Inf]
- **Evidence:** [13][20][21] [S]; dates [Snip]

### 2.16 Cover, final-model preview and foreshadowing insets

- **Looks like:** a cover render of the finished model, plus small insets showing a completed
  section before it is built [12].
- **Cognitive job:** states the goal up front and gives a progress check. Per UXmatters it
  "projects an aspirational vision" and reduces anxiety about whether the build is going
  right [12][S].
- **Rules:** show the *finished state of this chunk* before the steps, and keep the model
  consistent between inset and steps.
- **Mapping seed:** each chapter opens with "what you will have understood" as a drawing.
- **Evidence:** [12] [S]

### 2.17 Human elements: hands and minifigure

- **Looks like:** an illustrated hand showing how to operate a part (finger on a trigger), and
  the minifigure as a character and a fixed scale reference (about 4 cm tall) [12][Snip].
- **Cognitive job:** a **scale-and-affordance proxy** and an emotional anchor. McCloud argues a
  simple iconic character invites reader identification ("masking") [35][Snip].
- **Rules:** one recurring character, always the same shape. Hands only where an interaction
  needs showing.
- **Mapping seed:** a single recurring "reader proxy" figure. Damian, drawn as himself, is
  a natural candidate because the reader and the dogfood subject are the same person [Inf].
- **Evidence:** [12][35] [S/Snip]

### 2.18 QR code and the 3D builder app (digital layer)

- **Looks like:** a QR code linking to the digital instructions. The LEGO Builder app lets you
  zoom, rotate and view in 3D, with a "ghost view" for what is built versus what you are placing
  [6][Snip: app store and LEGO app pages].
- **Cognitive job:** a **reader-controlled** view. Tversky found interactivity (control of
  speed, zoom, orientation) can remove the weaknesses of animation [18][P].
- **Rules:** the paper page must stand alone. The digital layer adds viewpoint control, not
  new facts.
- **Mapping seed:** the published page can offer reader-controlled zoom into a callout. The
  static page stays the SSOT.
- **Evidence:** [6][18] [S/P]

### 2.19 Wordlessness (the meta-atom)

- **Looks like:** no sentences. Only numerals, pictures, arrows and symbols.
- **Cognitive job:** kills the **split-attention** cost of mapping text to picture (Chandler &
  Sweller [22]) and the **redundancy** cost of text repeating a picture [20]. It also makes one
  print run readable in every language [28][Snip].
- **Rules / limits:**
  - The constraint forces designers to "think very hard about how to explain things"
    [Snip: study.com result; not read].
  - Wordless excludes blind readers. LEGO's audio/braille pilot converts steps into
    "step by step text-based descriptions" [15][S].
  - The FAA report's own recommendation is that *some* text "to focus attention, highlight
    concepts, and simplify complex pictorials/pictograms" would help [27][P]. Schmidt &
    Kysor found cards with words *integrated into* diagrams ranked higher [27][P].
  - Neurath: "Words are never banished. Pictures are there to help." [30][S].
- **Mapping seed:** the Manual relaxes the rule (Jarad's own call): **words are labels glued
  to the thing they name**, never paragraphs. Every page also carries a hidden text
  description (alt text) as the audio/braille equivalent. See section 5.
- **Evidence:** [15][20][22][27][28][30] [P/S]

---

## 3. Why a wordless picture page works (the evidence stack)

### 3.1 Mayer's principles read against the LEGO page

Definitions are Mayer (2009) as quoted in the Harvard CHDS monograph [20]. Effect sizes are
from a secondary summary [21] and are **indicative, not verified against the book**.

| Mayer principle | Definition (short) | LEGO atom that embodies it | Rule it implies for the Manual |
|---|---|---|---|
| Coherence (d=0.86) | Exclude extraneous material | White/light backgrounds, one build focus per page, no decoration [9] | Nothing on the page without a job. Tension with humor, see 5.5. |
| Signaling (0.69) | Add cues that show what is essential | New-part highlight [7][9] | One highlight colour, one meaning. |
| Redundancy (0.10) | Do not repeat the same content in a second form | Wordless pages | Label once; never write the sentence the picture already says. |
| Spatial contiguity (0.82) | Put words near their picture parts | Callout box beside the step; part labels on the part | Label touches the thing. No far-away legend keyed by letter. Byrne dropped letters for this reason [31]. |
| Temporal contiguity (1.31) | Present words and pictures at once | (n/a on paper; matters for narration) | If a page is narrated, narrate while it is on screen. |
| Segmenting (0.67) | Learner-paced segments | Steps, bags, page turns | One page, one idea. No scroll-to-continue. |
| Pre-training (0.78) | Teach names and characteristics first | Parts box, inventory, overview page | A "meet the parts" legend before any assembly page. |
| Modality (1.00) | Narration beats printed text with graphics | (not used) | Optional spoken walkthrough of a page frees the eyes. Hypothesis. |
| Multimedia (1.35) | Words plus pictures beat words alone | Pictures with symbols | Never ship a words-only page. |
| Personalization (1.00) | Conversational style | (not used) | Labels in plain talk; "your Mac Studio", not "the node". |
| Generative activity (0.71) | Learner summarizes or explains | (implicit in building) | **Damian's tell-back is itself a generative activity.** Put a "now tell it back" frame on every page. |

Boundary conditions: effects are stronger for novices, complex material and system-paced
delivery [21]. That describes Damian well.

### 3.2 Other supporting results

- **Split attention** (Sweller, Chandler): learners must mentally integrate separated text and
  diagram, which costs load. Integrated presentation gives better learning [22][S].
- **Congruence and Apprehension principles** (Tversky, Morrison, Betrancourt 2002).
  Congruence: the representation's structure should match the intended mental
  representation. Apprehension: it should be "readily and accurately perceived and
  comprehended". They also say graphics "should lean toward the schematic and away from the
  realistic, an inclination that does not come naturally to many programmers, who delight in
  graphic richness and realism" [18][P]. Arrows work for sequence and direction, and
  "schematizing is simpler than it sounds; clear understanding is a prerequisite" [18][P].
- **Arrows carry causal meaning.** Without arrows, people read a diagram as structure; with
  arrows, as function and process. In causal descriptions, people drew arrows for the sequence
  of actions and often did not label parts [19][Snip]. So an arrow is a strong statement.
  Spend it carefully.
- **Step-by-step beats one big diagram** (Novick et al. 2000, confirmed by Agrawala's
  experiments). Highly-ranked instructions led to less assembly time and fewer errors [17][P].
- **Diagrams beat photographs** because they "require less study to distinguish important from
  insignificant details" (Dwyer 1967, cited in the FAA report) [27][P]. Schematic over
  realistic.
- **Pictures are remembered better than words** (Standing 1973 recognised 83% of 10,000
  pictures against 14% for words, per a summary) [24][Snip]. The *mechanism* is disputed. A
  2025 paper argues distinctiveness, not dual coding, explains it [24][Snip]. Use the effect,
  do not build theory on the mechanism.
- **People scan.** NN/g found 79% of test users always scanned a new page and 16% read
  word by word (1997) [25][Snip]. This is Damian's "wall of text" freeze, measured.
- **Expert blind spot.** Designers who know the content cannot judge what a novice sees. The
  FAA report says card designers "know the information so well" that they disregard what
  detracts, and that failure to test hides it [27][P][26][S]. Jarad drawing the pages cannot
  validate them.

---

## 4. Other traditions: transferable tricks

| Tradition | Trick worth stealing | Rule | Caveat |
|---|---|---|---|
| **IKEA** | Show part, orientation, intended result, **wrong result**, next connection; same arrow style and part-count placement everywhere; early "wins" (frame first) before refinement; tested "when a test person manages to assemble the product without any written text" [28][29] | Design the first three steps for a quick win. Test with a naive builder. | IKEA's written rationale is third-party. Cultural scrutiny forced a gender-neutral figure [28][S]. |
| **Airline safety cards** | A test protocol: open-ended comprehension, Jentsch's three-way scoring, ISO 9186 (67%) / ANSI Z535 (85%) acceptance thresholds [27] | Score tell-backs as complete / incomplete-but-safe / wrong. Treat "wrong" as the failure. | 65% mean comprehension shows pictures alone fail on unfamiliar referents. |
| **Isotype (Neurath, Reidemeister, Arntz)** | Repeat a unit, do not enlarge it; the same sign always for the same thing; flat silhouette, no perspective; a "transformer" role that turns facts into a picture-sketch [30] | Draw counts as repeated same-size icons. Keep one icon per concept. | "Never intended to replace verbal language" [30]. |
| **Byrne's Euclid (1847)** | Colour and shape *are* the labels, so the reader never decodes letters. Primary colours plus black for maximum differentiation; black kept off large areas; hybrid colour-plus-letter sometimes speeds recognition [31] | Pick a small fixed palette where each colour names a concept. | Colour-coded sets fail for colour-blind readers; add shape/pattern redundancy [Inf]. |
| **Richard Scarry (Busytown)** | Cutaway "every wall is see-through" scenes; labels on every object; recurring characters; jokes help memory; researched how things worked for months before drawing [33] | Research the real mechanism before drawing. Recurring cast. | Humor vs coherence, see 5.5. |
| **Scott McCloud (Chrome comic, 2008)** | About 20 engineer interviews adapted into ~38 pages; a reviewer called the graphics "simplified, but entirely accurate" [34]. His theory: "amplification through simplification" and a simple iconic character for identification [35][Snip] | Interview the people who built it; draw only what survives their review. | The Chrome comic's own techniques are described only thinly in what I could read. |
| **Thing Explainer / Up Goer Five (Munroe)** | Labelled blueprint diagrams of complex machines using only the 1,000 most common words [36][Snip] | Fix a controlled vocabulary for the grammar, and every term appears in the legend. | The vocabulary cap forces plain words even for precise ideas. |
| **Lin Clark's code cartoons** | Analogy first ("kids passing notes in class"), extended consistently (locked envelope = encrypted message); flags its own simplification: "this diagram is a little oversimplified" and then repairs it [37] | When a picture is deliberately simplified, say so on the page and say where the full picture is. | Her explicit "simplification marker" is the atom LEGO lacks. |
| **Phippy (Illustrated Children's Guide to Kubernetes)** | Map each technical concept to a *character* (PHP giraffe, owl, ship made of rafts) and a story; "metaphorical thinking can really resonate with people and help them understand something very quickly" [38] | One concept, one character, stable for the whole book. | The authors concede it is "clearly not the pinnacle of technical documentation" [38]. Accuracy needs a second layer. |
| **Harry Beck's Tube map (1931)** | Discard scale and geography, keep topology; 0/45/90 degree lines; ticks for ordinary stops and diamonds for interchanges [39] | State what the diagram preserves and what it deliberately distorts. | Beck's employer thought it too radical at first [39]. |
| **Julia Evans / Wizard Zines** | "Get specific" scenes rather than generalities; fundamentals that last [40][Snip] | Teach one concrete scene per page. | Snippet only. |

---

## 5. Tensions and traps for I-10

### 5.1 "How" versus "why"
A LEGO page shows actions, and the graphic-instruction rule of thumb reviewed in the FAA
report is "focus on actions, not reasons" [27]. The Manual's outcome is *reasons* (why an
event bus). Two ways to carry a why in a picture:
the **analogy bridge** (Lin Clark [37], Phippy [38]) and the **wrong/right pair** (IKEA,
LEGO check/X [6][29]). Combine them so the reader sees the false model crossed out next to the
true one. [Inf]

### 5.2 Structural versus action diagrams, and the "stud"
See finding 2. If 33GOD has one universal connector, name it and draw it like a stud. If it
has several, give each its own typed line (event, call, store, ownership). Agrawala's own
guideline convention is a precedent: **dotted** line for fasteners, **arrow** for a significant
part being brought in [17]. Check the architecture against live code to find out which case
applies. I did not.

### 5.3 Novel symbols fail without teaching
Of 12 symbols tested on kids, only two achieved universal comprehension, and both reuse
conventions the kids already knew [6]. The FAA's familiar ANSI symbols scored over 90% [27].
Rule of thumb: every new atom is introduced on the legend page and reused unchanged. Keep the
symbol count small. LEGO ships about 12 and loses half.

### 5.4 Scale bar and nesting meter
See 2.7 and 2.8. Do not claim LEGO precedent for a nesting meter. The precedent is for a
submodel callout and for a bar used as a *calibration*. A persistent "you are here" strip,
like a Tube-map line diagram, has transit precedent [39]. Pick on what Damian can tell back.

### 5.5 Humor versus coherence
Mayer's coherence principle lists "humorous graphics" among extraneous material [20]. Scarry
argues jokes make things memorable [33]. These can both be right if the **joke carries the
mechanism** (a character whose behaviour *is* the concept) and does not sit beside it as
decoration. [Inf]

### 5.6 Accessibility
A wordless manual locks out blind readers. LEGO piloted AI-generated step descriptions for
screen readers and Braille [15]. For the Manual, every page should ship with a text
description as a first-class twin, which also doubles as the page source's evidence trail.
[Inf]

### 5.7 Who validates
Jarad cannot (expert blind spot [26][27]). Damian is the gate, scored with the three-way
rubric. Note n=1 and that Damian already runs a peer on a Mac Studio, so he is not a true
novice. A genuinely naive second reader would be a stronger test. [Inf]

---

## 6. Layout rules distilled

1. **One page, one step.** One new idea per page. No scroll to continue (segmenting [20]).
2. **At most ~4 new chunks per page.** Cowan's limit [23][Snip]. Nesting depth on one page: 3-4 [14].
3. **Words are labels glued to the thing they name**, never paragraphs (spatial contiguity [20];
   FAA: integrated words ranked higher [27]).
4. **One highlight, one meaning.** Reserve one colour for "new on this page" [13][20].
5. **Legend first.** Teach every symbol and part name on page 0 before using them
   (pre-training [20]; LEGO inventory [13]).
6. **Same thing, same picture, everywhere.** Never re-draw a component differently between
   pages (Isotype [30]; IKEA consistency [29]).
7. **Draw counts as repeated same-size units**, not enlarged shapes (Isotype [30]); encode
   hierarchy in discrete steps (Tversky [18]).
8. **Show the wrong picture, crossed out, next to the right one** wherever a false model is
   likely [6][29].
9. **Reuse conventions the reader already knows** (check/X, rotate arrow) and teach everything
   else [6][27].
10. **Fixed, small connector vocabulary.** Same arrow style, same perspective, same place for
    counts and warnings [29]. Typed connectors if components connect differently [17].
11. **Schematic over realistic.** Lean schematic, say what is preserved and what is distorted
    (Tversky [18], Beck [39], Dwyer [27]).
12. **Mark every deliberate simplification** and point to where the fuller picture lives
    (Lin Clark [37]).
13. **Repeat twice, then multiply.** Show the first two in full, then `xN` [17].
14. **Each chapter ends on a finished picture** ("you built X") [12].
15. **Ship a text twin** for every page [15].
16. **Test with a tell-back and score three ways** (complete / incomplete-but-safe /
    wrong) [27]. Treat "wrong" as the only fail.
17. **Starting word budget (hypothesis, to tune from tell-backs):** labels of 1-3 words; no
    sentence on a page. Unsourced. The grammar task should set the real number.

---

## 7. Source ledger

Confidence follows the tags at the top. "Fetched" means I read the page text through the fetch
tool. Pages that returned 403/402/521/TLS errors are listed at the end.

**Local**

- [1] `/home/delorenj/code/33GOD/THE_MANUAL.md` [P], the vision.
- [2] `/home/delorenj/code/33GOD/_bmad-output/planning-artifacts/initiatives.md`, section "I-10
  The Manual" [P].

**LEGO**

- [3] LEGO, "How we design our building instructions" https://www.lego.com/en-us/service/help-topics/article/how-we-design-our-building-instructions [P]. Team starts "with 3D software that was created just for us", decides "how many pieces to add in each step" and the angle, and builds "from the ground up".
- [4] LEGO, "Building instructions through time" https://www.lego.com/en-us/history/articles/d-lego-building-instructions-through-time [P]. Quotes the 1983 team ("In 1983, the LEGO group sets up a specialized building instruction team for the first time...").
- [15] Gizmodo, LEGO audio/braille instructions https://gizmodo.com/lego-is-finally-introducing-audio-and-braille-building-1837621676 [S].

**Fan and trade sources on LEGO symbols and history**

- [5] BricksFanz symbol guide https://bricksfanz.com/a-guide-to-lego-instructions-symbols/ [S]
- [6] BrickNerd, kid test of 12 symbols https://bricknerd.com/home/the-meaning-of-lego-instructions-symbols-10-11-23 [S]
- [7] BrickNerd, "How LEGO instructions have changed" https://bricknerd.com/home/how-lego-instructions-have-changed-over-time-a-forest-of-discovery-10-17-22 [S]
- [8] Brickset, "The simplification of the LEGO building experience" https://brickset.com/article/110723/the-simplification-of-the-lego-building-experience-what-s-up-with-that [S] (first ~100k of ~390k characters read)
- [9] Brickset, black backgrounds, 1 Mar 2021 https://brickset.com/article/58147/lego-to-ditch-the-black-backgrounds-in-instruction-manuals [S]
- [10] Rambling Brick, the 2022 statement https://ramblingbrick.com/2022/05/28/the-new-building-instruction-design-official-statement-and-editorial-rant/ [S]
- [11] BricksFanz, style update https://bricksfanz.com/update-about-new-build-instructions-style/ [S]
- [12] UXmatters, "Inspirations from a LEGO instructional booklet" https://www.uxmatters.com/mt/archives/2020/12/inspirations-from-a-lego-instructional-booklet.php [S]
- [13] The Earl of Bricks, Stud.io instruction builder guide https://theearlofbricks.com/blog-studio-instruction-builder/ [S, opinionated]
- [14] Open L-Gauge, Studio instruction guide https://open-l-gauge.eu/making-building-instructions-in-studio/ [S]

**Cognition and design research**

- [17] Agrawala, Phan, Heiser, Haymaker, Klingner, Hanrahan, Tversky, "Designing Effective Step-By-Step Assembly Instructions", SIGGRAPH 2003 https://courses.ischool.berkeley.edu/i247/f05/readings/Agrawala_Assembly_SIGGRAPH03.pdf (ACM DOI 10.1145/1201775.882352) [P, full text read]
- [18] Tversky, Morrison, Betrancourt, "Animation: can it facilitate?", IJHCS 57, 2002 https://hci.stanford.edu/courses/cs448b/papers/Tversky_AnimationFacilitate_IJHCS02.pdf [P, text read]
- [19] Heiser & Tversky, "Arrows in Comprehending and Producing Mechanical Diagrams", Cognitive Science 30, 2006 https://onlinelibrary.wiley.com/doi/abs/10.1207/s15516709cog0000_70 [Snip, abstract only]
- [20] Mayer (2009) principles as quoted in the Harvard CHDS monograph https://media.repository.chds.hsph.harvard.edu/static/filer_public/ca/62/ca625803-3d73-4855-b3e1-765870ce3772/2023_jwaxman_monograph_cogtheory_multimed.pdf [P, text read]
- [21] Coursebox summary with effect sizes https://www.coursebox.ai/blog/mayers-cognitive-theory-of-multimedia-learning [S, numbers unverified]
- [22] Split-attention effect (Wikipedia) https://en.wikipedia.org/wiki/Split_attention_effect [S]; Chandler & Sweller 1991 https://www.semanticscholar.org/paper/THE-SPLIT%E2%80%90ATTENTION-EFFECT-AS-A-FACTOR-IN-THE-OF-Chandler-Sweller/d81d3e4514b69578aaa769d888adade75355b563 [Snip]
- [23] Cowan 2001, "The magical number 4 in short-term memory" https://philpapers.org/rec/COWTMN [Snip]
- [24] Picture superiority: https://en.wikipedia.org/wiki/Picture_superiority_effect [Snip]; Higdon et al. 2025 https://journals.sagepub.com/doi/10.1177/17470218241235520 [Snip]
- [25] NN/g, "How Users Read on the Web" https://www.nngroup.com/articles/how-users-read-on-the-web/ [Snip]
- [26] Curse of knowledge https://en.wikipedia.org/wiki/Curse_of_knowledge [Snip]
- [27] Corbett, McLean, Cosper, "Effective Presentation Media for Passenger Safety I: Comprehension of Briefing Card Pictorials and Pictograms", DOT/FAA/AM-08/20, 2008 https://libraryonline.erau.edu/online-full-text/faa-aviation-medicine-reports/AM08-20.pdf [P, text read]

**Other traditions**

- [28] Justin Zhuang, "Wordless Instructions" (IKEA; cites Pehrson & Zimmerdahl) https://justinzhuang.com/posts/wordless-instructions/ [S]
- [29] Sketchboat, "The IKEA manual: the UX of building furniture" https://www.sketchboat.com/blog/the-ikea-manual-the-ux-of-building-furniture-and-why-it-works [S]
- [30] Isotype: https://en.wikipedia.org/wiki/Isotype_(picture_language) [S]; Eye magazine, Neurath archive https://eyemagazine.com/feature/article/archive-international-picture-language [S]; Isotype Revisited https://isotyperevisited.org/2012/08/introduction.php [S]
- [31] Tufte, *Envisioning Information* ch. 5 on Byrne https://gwern.net/doc/design/typography/rubrication/1990-tufte-envisioninginformation-ch5-byrneseuclid.pdf [P, 4 pages read]
- [32] Byrne title page (Yale catalogue) https://collections.britishart.yale.edu/catalog/alma:99160423408651 [Snip]
- [33] Simon Rogers on Scarry https://simonrogers.net/2025/09/01/how-richard-scarry-taught-me-everything-i-know-about-visual-storytelling/ [S]
- [34] McCloud, Chrome comic https://www.scottmccloud.com/googlechrome/ [S]; TidBITS https://tidbits.com/2008/09/01/google-explains-its-forthcoming-web-browser-with-comics/ [S]
- [35] *Understanding Comics* summary https://www.ebsco.com/research-starters/literature-and-writing/understanding-comics-invisible-art-scott-mccloud/ [Snip]
- [36] Thing Explainer https://en.wikipedia.org/wiki/Thing_Explainer [Snip]
- [37] Lin Clark, "A cartoon intro to DNS over HTTPS" https://hacks.mozilla.org/2018/05/a-cartoon-intro-to-dns-over-https/ [S]
- [38] CNCF, Karen Chu and Matt Butcher on Phippy https://www.cncf.io/humans-of-cloud-native/karen-chu-and-matt-butcher-simplifying-the-complex-with-phippy/ [S]
- [39] Tube map https://en.wikipedia.org/wiki/Tube_map [S]; London Transport Museum https://www.ltmuseum.co.uk/collections/stories/design/transforming-tube-map-harry-becks-iconic-design [Snip]
- [40] The New Stack on Julia Evans https://thenewstack.io/julia-evans-bite-size-zines-break-it-down/ [Snip]

**Unreachable (not used as evidence):** brickfanatics.com (403, both pages), fastcompany.com
IKEA article (403), ostraining.com (403), study.com (403), Brickipedia (402), MAA Byrne page
(521), stepalong.com (TLS error). The Agrawala, FAA, Tversky and Mayer files were downloaded as
PDFs and converted with `pdftotext` into `/tmp/manual-research-pdf/` (scratch, not part of the
repo).

**Not verified:** nothing about the 33GOD architecture, component names or the NATS/Dapr claims
was checked against live code here. The mapping seeds use Jarad's own names from THE_MANUAL.md.
The grammar task must verify each drawn claim against code, per the I-10 acceptance criteria.
