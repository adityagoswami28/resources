# Storyboard format

One JSON file. Write it compact (no pretty-printing).

```json
{"title":"How Bees Make Honey","style":"cut-paper","cover":{"colour":"#b7791f","piece":"bee"},"music":"gentle","air":"birds",
 "pieces":{"hive":[ ...shapes... ]},
 "pages":[{"say":"Spoken sentence for this page.",
   "floor":{"ground":"grass"},
   "far":[{"use":"hills","s":0.24,"mat":"rockFar"},{"use":"sun","x":0.4,"y":0.6,"s":0.36,"rays":true}],
   "left":[{"use":"tree","x":-0.58,"s":0.86},{"use":"hive","x":-0.36,"y":0.2,"s":0.3,"id":"hive"}],
   "front":[{"use":"grass","s":0.12}],
   "fly":[{"use":"bee","s":0.12,"from":["right","fl"],"to":["left","hive"],"n":3}],
   "focus":"left"}]}
```

Top level: `title` (printed on the front cover, up to about 40 letters), `style`, `pieces` (your own drawn pieces, optional), `pages`, `seed` (optional number, changes the random details), and three that make the book fit its topic:
- `cover`: `{"colour":"#b7791f","piece":"bee"}`. `colour` = the cover cloth (darker colours look best). `piece` = any piece, yours or ready-made, shown on the cover above the title (it is sized to fit; options go in as `{"use":"flower","mat":"pink"}`). Left out: a colour picked from the title and a plain gold sun.
- `music`: `gentle` (music box) · `bright` (marimba, quick) · `curious` (plucked, a little mysterious) · `dreamy` (slow bells) · `stately` (harp, old-book) · `none`.
- `air`: `birds` · `night` · `quiet`.

## A page

| key | what |
|---|---|
| `say` | the narration for this page. The page stays open as long as the sentence takes |
| `far` `back` `mid` `left` `right` `front` | standing sheets of card, far to near. Each is a list of pieces. Leave out the ones you don't need |
| `floor` | the flat page under the pop-ups |
| `fly` | things that fly between two spots |
| `slider` | one piece that slides along a slot at the front (pull-tab), e.g. `{"use":"boat","s":0.1}` |
| `focus` | `left`, `centre` or `right`: where the camera drifts |
| `caption` | a few words printed on the floor (pages after the first) |
| `life` | `{"birds":3,"mist":false}` |

### The sheets

x runs left to right, 0 is the fold. y is height.

| sheet | x range | max height | use for |
|---|---|---|---|
| far | -0.96..0.96 | 0.91 | sky, hills, the tallest backdrop |
| back | -1..1 | 0.74 | second row |
| mid | -1..1 | 0.66 | middle row |
| left | -1.02..-0.10 | 0.88 | a big piece on the left |
| right | 0.10..1.02 | 0.88 | a big piece on the right |
| front | -1..1 | 0.34 | grass, small things, labels |

### A piece on a sheet

`{"use":"tree","x":-0.5,"y":0,"s":0.6}`: `x` = where its middle sits, `y` = how high its base is (default 0), `s` = its height. Optional: `mat` (colour), `flip`, `id` (a name so flyers can aim at it), plus the piece's own options.

Sizing: a piece's width is its height `s` times the `w` number below (a tree with s 0.8 is about 0.7 wide), so its edges are at x ± s·w/2. Keep those inside the sheet's x range and neighbours from overlapping. A piece that still pokes off its sheet is slid back in, or shrunk if it is simply too big.

## Ready-made pieces (default height, w = width ÷ height, options)

Nature: `tree` (0.45, w0.9; mat, fruit = a colour for fruit dots), `pine` (0.45, w0.6), `bush` (0.14, w2.7), `grass` (a row across the sheet; s 0.12), `flower` (0.25, w0.4; mat, centre, petals), `rock` (0.1, w1.6), `hills` (rolling hills across the sheet; s 0.2, bumps, mat), `peak` (0.5, w0.5; a tall crag), `mountain` (0.5, w1.3; snow), `cloud` (0.12, w3.5), `sun` (0.5, w1; y is its centre; rays, mat. Use `"mat":"white"` for a moon), `fall` (waterfall, 0.4).
Made things: `house` (0.3, w1.1; mat, roof, glow), `tower` (0.5, w0.4; floors, cols), `boat` (0.1, w2.4), `lantern` (0.05; glows), `sign` (0.2, w0.4; text), `person` (0.12, w0.5; mat, hat, staff, pack).
Animals: `heron` (0.3, w0.7), `toucan` (0.1, w1.2), `monkey` (0.09, w0.8).
Explaining: `label` (`text`; s = letter height 0.05 to 0.08; `banner` false for bare words), `arrow` (from x,y `to`:[x,y]; s = thickness 0.02; bend).

## Colours

Anywhere a colour is asked for use a name or `#rrggbb`. Every look restyles them to match.
Names: `red yellow pink orange cream white navy brown slate black tan straw maroon darkRed glow` · `leaf leafLight leafDark meadow grass` · `rock rockFar rockNear` · `wood woodLight sand` · `water foam` · `sun gold ink paper`.

## Floor

`{"ground":"grass","dots":"leafLight","path":{"pts":[[-1.2,-0.3],[0,-0.5],[1.2,-0.6]],"w":0.09},"river":{"pts":[...],"w":0.14},"ponds":[[x,y,rx,ry]],"labels":[{"text":"Meadow","at":[-0.5,-0.6]}]}`
Floor x runs -1.25..1.25, y -0.95 (near you) ..0.95. `ground` is any colour. A river makes the water sound.

## Flying things

`{"use":"bee","s":0.12,"from":["left","big"],"to":["mid","f2"],"n":2,"secs":2.5}`
`from`/`to` are spots: `[sheet, id]` (a piece you gave an `id`, or an `anchor` in a drawn piece), `[sheet, x, y]`, or `["floor", x, y]`. `n` = how many, `secs` = one trip, `loop` false = go once, `arc` = how high it swoops.

## Drawing a new piece

Add it under `pieces` as a list of shapes, back to front, then `use` it like any other. Draw inside a box: x -0.5..0.5, y 0 (base) to 1 (top). About 5 to 15 shapes is plenty.

```json
"jar":[{"rect":[-0.3,0,0.3,0.74,0.1],"mat":"#f0ae28","id":"glass"},
       {"oval":[-0.19,0.4,0.045,0.26],"mat":"white","kind":"hi","in":"glass"},
       {"rect":[-0.34,0.72,0.34,0.88,0.04],"mat":"red"},
       {"text":"honey","at":[0,0.3],"size":0.14}]
```

Shapes: `circle`[x,y,r] · `oval`[x,y,rx,ry,turn°] · `rect`[x0,y0,x1,y1,corner] · `poly`[[x,y],…] · `ngon`[x,y,r,sides,turn°] · `curve`[[x,y],…] (smooth closed outline) · `blob`[x,y,rx,ry] (wobbly) · `cloud`[x,y,rx,ry,bumps] · `leaf`[x,y,angle°,length,width,bend] · `stroke`[[x,y],…] with `w` (a thick line; `sharp` for corners) · `text` with `at`,`size` · `line`[[x,y],…] (thin ink line).

On any shape: `mat` (colour), `kind` (`fill` default, `shade` = soft shadow, `hi` = highlight), `id` (name it), `in` (cut it to fit inside a named shape), `anchor` (name a spot flyers can aim at), `glow` true (it lights up), `tone` (-0.3 darker .. 0.3 lighter).

Repeat shapes in rows: `{"grid":[cols,rows,dx,dy,stagger],"of":[ ...shapes... ]}`.
