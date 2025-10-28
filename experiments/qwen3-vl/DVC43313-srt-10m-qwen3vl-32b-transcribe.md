Experiment to test ability of Qwen3-VL to read subtitles

Annotated errors in first experiment between [].
[???] hallucination
[/] slightly different
[//] v. different

Observations:
* transcription is worse on first 10 minutes when the model get a 20 minutes video
* transcription is generally not accurate, some sentences come from nowhere, many are transformed or tehir meaning corrupted
* there are also a lot of generally ok sentences that preserve some meaning

---

* Time: 2025-10-28T10:42:40.516170
* Video: v-10-srt.mp4
* Model: Qwen/Qwen3-VL-32B-Instruct
* Device: NVIDIA A100 80GB PCIe
* VRAM used: 62.60 GB

PROMPT:

The video is a broadcast television recording from Northern Ireland. Transcribe all the subtitles.

ANSWER:

```
We were calling 6 limited companies.
UTV LIVE
TX
HEADS/ALS05
RX/TX: 01/03/2017
40/24
We were calling 6 limited companies.
[MISSING LINES]
The judge has ruled that corporate companies in receipt of RHA subsidies
can be named by the Department for the Economy.
However Mr Justice Deeny prohibited the Minister Simon Hamilton
[summary] from publishing the names of individual recipients.
That means the names of the companies involved have been revealed.
[minor] These names won't be published until any appeals they have to being named are
considered.
[wrong name] Our correspondent Jane Louchrey has a report.
So companies can, individuals can't.
[???] Which means, really, the principle had to be reversed.
So they've got a clear contact with the head
[???] from these documents or their, in a financial language,
they have to convert that into penalty options.
[???]So we wouldn't be able to do that.
[???]So, bye-bye.
[???] Fu[**] yeah.
[???]While are they doing?
Okay.
One minute.
UTV LIVE
TX
HEADS/ALS05
RX/TX: 01/03/2017
40/24
One minute.
Hello and welcome.
[invented surnames] You're watching UTV Live at 6 with Paul Gilmour and Fiona.
Good evening. These are the stories making the headlines.
A judge has ruled that corporate companies in receipt of RHA
subsidies can be named by the Department for the Economy.
[???] That's at the offices of the Department for the Economy in the Seaview Plaza.
[mangled] I hope, when I see Belfast basically and the rest of the city, which is what we really want,
we're part of the city. We're not some independent bit of it. We're actually part of Belfast.
[???] The Department for the Economy is now on the case.
[vcorrup] Also tonight, a fire-dress been the remarkable costume costume who saved a little boy's life.
And the wonderful season of spring has sprung. It's just over six weeks to Easter.
Will the weather do us any favours? I'll check the detail here later in the programme.
A judge has ruled that corporate companies in receipt of RHA
subsidies can be named by the Department for the Economy.
However, Mr Justice Deeny prohibited the Minister Simon Hamilton
[-sum] from publishing the names of individual recipients.
That means the names of the companies involved have been revealed.
[sum] These names won't be published until any appeals they have to being named are
considered.
Our correspondent Jane Louchrey has a report.
The RHA initiative was set up to encourage businesses
to move from fossil fuels to renewable heating systems.
[/] But the benefit was, in controversy and debate, and for many,
[/] the more money, the more fuel they burned.
The Economy Minister was under a little bit of
transparency to publish the names of the recipients each month.
But 500 boiler owners, some companies, some individuals,
went to court to stop the publication of their details,
arguing they would be a media blinding frenzy if they were released.
A Department of Justice inquiry and the Department
[wong] of the Economy could not come to an agreement.
[//] So we had an inquiry, and the judge in that inquiry
has now ruled on the matter from the High Court.
Jane Louchrey with the details outside the courts.
The judge said the court is not looking at the reason why
general release of the names and the damage to the economy
because of the names.
Indeed, he said one well-known company, he said, which had seven boilers
[/] and had received £625,000 from the scheme since July 2014.
The judge asked there may well be legitimate reasons for that,
and they could be explained to any
bystander, journalist or member of the public.
On a more general level, the application for an RHA subsidy
did not amount to a public-facing document,
and the Department had the right to vary the terms.
The judge said the Department was not obliged to publish the names.
He agreed with the boiler owners, who
argued the economy minister shouldn't publish the names
in order to defeat an action brought by the party and the Department.
The judge said the court could not draw the conclusion
that the Minister had acted in bad faith.
The lawyer acting for the Renewable Heat Association
said the judge's decision to be appealed.
The association said members would now be able to respond to the decision as a call for the verdict.
When the court convened, the counsel for the boiler owners said
they had hoped to extend the reduction.
The Department for the Economy is now to publish the names of the companies involved.
And Jane, join us now.
Jane, what will be the consequences for the Department for the Economy?
[//] Jane Louchrey: Well, the judge has said the Department may not act
[//] in a way that is contrary to the law.
And he's also said that the Department, the government,
[//] must act in a way that's proportionate.
[//] And that's the key issue.
[//] And the Department will have to decide whether it's proportionate to publish the names.
And if it does, it will have to do so in a way that's fair and balanced.
And the burden for the Department for the Economy is to satisfy
the court that the publication of the names
was proportionate and necessary.
And the judge said the Department had a duty to act in a way that's fair and balanced.
Well, has there been any reaction at all from the Renewable Heat Association?
Jane Louchrey: There's been no formal reaction.
And the association says that the judge's ruling was
of great importance and that most publicly available data by the RHA scheme
could be published and required disclosure.
The RHA, remember, is a government initiative to encourage businesses to move from fossil fuels to renewable heating systems.
And the Department for the Economy will have to decide whether to publish these names.
And the judge said the Department had a duty to act in a way that's fair and balanced.
And the Department will have to decide whether to publish the names.
And the judge said the Department had a duty to act in a way that's fair and balanced.
And the Department will have to decide whether to publish the names.
And the judge said the Department had a duty to act in a way that's fair and balanced.
And the Department will have to decide whether to publish the names.
And the judge said the Department had a duty to act in a way that's fair and balanced.
And the Department will have to decide whether to publish the names.
And the judge said the Department had a duty to act in a way that's fair and balanced.
And the Department will have to decide whether to publish the names.
And the judge said the Department had a duty to act in a way that's fair and balanced.
And the Department will have to decide whether to publish the names.
And the judge said the Department had a duty to act in a way that's fair and balanced.
And the Department will have to decide whether to publish the names.
And the judge said the Department had a duty to act in a way that's fair and balanced.
And the Department will have to decide whether to publish the names.
And the judge said the Department had a duty to act in a way that's fair and balanced.
And the Department will have to decide whether to publish the names.
And the judge said the Department had a duty to act in a way that's fair and balanced.
```

* VRAM used: 70.81 GB


---


* Time: 2025-10-28T16:33:45.728572
* Video: v-10-srt.mp4
* Model: Qwen/Qwen3-VL-32B-Instruct
* Device: NVIDIA H100 NVL
* VRAM used: 62.70 GB

PROMPT:

The video is a broadcast television recording from Northern Ireland. Transcribe all the subtitles with high accuracy. One sentence per line. Don't make things up.

ANSWER:

```
We were calling 6 limited companies.
UTV LIVE
TX
HEADS/AL505
RX/TX: 01/03/2017
40:04
We were calling 6 limited companies.
They were two of the subsidiaries of the same company.
They were calling 6 limited companies.
Do you want to sit here?
Do you want to sit on the floor?
Our judge has ruled that corporate companies in receipt of RHA subsidies can be named by the Department for the Economy.
However, Mr Justice Deeney prohibited the Minister, Simon Hamilton, from publishing the names of individuals who received money from the Renewable Heat Incentive.
These names won't be published until any decisions they have to being launched in the properly considered.
Our correspondent Jane Lockrey was in court.
So companies can, individuals can't.
What damage, really, by the principle, has it caused, if at all?
So they've got a clear contact with the head.
If they have those documents, or their, in a financial language, they have to convert that into pleasing options.
So we wouldn't be left in peace.
So, bye-bye.
Fuck yeah.
While are they doing?
Okay.
One minute.
One minute.
UTV LIVE
TX
HEADS/AL505
RX/TX: 01/03/2017
40:04
One minute.
One minute.
Hello and welcome.
Hello and welcome.
You're watching UTV Live at 6 with Paul Cline and Joyce.
Good evening. These are the voices making the headlines.
A judge has ruled that corporate companies in receipt of RHI subsidies can be named by the Department for the Economy.
The latest on the RHI scandal in Northern Ireland. Seamus Keys, the man who's been behind the scheme, is now in court.
I hope, with East Belfast basically and the rest of the city, which is what we really want.
We're part of the city. We're not some independent bit of it. We're actually part of Belfast.
The Department for the Economy was in the dock.
Back with the story. The 600,000,000.
Also tonight, a fireman hero, the remarkable costume costume who saved a little boy's life.
Weather. The wonderful season of spring has sprung. It's just over six weeks to Easter.
Will the weather do us any favours? I'll show the detail here later in the programme.
A judge has ruled that corporate companies in receipt of RHI subsidies can be named by the Department for the Economy.
However, Mr Justice Deeney prohibited the Minister, Simon Hamilton, from publishing the names of individuals who received money from the Renewable Heat Incentive.
These names won't be published until any decisions they have to being launched in the properly considered.
Our correspondent Jane Lockrey was in court.
The RHI initiative was set up to encourage businesses to move from fossil fuels to renewable heating systems.
But the boxes enrolled in controversy and debate, and the brand.
At the end of the week, it was completely a lot more money, the more fuel they burned.
The Economy Minister was given a little chance of transparency to publish the names of the recipients, as month.
But 500 boiler owners, some companies, some individuals, went to court to stop the publication of these details.
Arguing they would be a media feeding frenzy if they were released.
The judge said the court has the power to order the names to be published, and that the names should be published by the North of the North.
Jane Lockrey with more on the story.
Jane Lockrey with more on the story.
The judge said the court has the power to order the names to be published, and that the names should be published by the North of the North.
However, any individual's name, and the organization any name, and the organization, any of the magazine budget.
That this is not a good enough reason to grant the injunction.
The judge said the court is not forbidding the names, any present, or future, of the scheme, and changes to the economy.
Because there's no payment.
Indeed, he cited one well-known company, he said, which had seven boilers and had received 800,000 from the scheme since July 2014.
The judge asked, there must be legitimate reasons for that.
And they would be explained to any lawyer, journalist or member of the public.
Mr Justice Deeney ruled the application for an RHI subsidy did not amount to a legal binding contract.
And the Department had the right to vary the terms.
The judge also said the Department was not bound by any contract.
He agreed with the boiler owners, who argued the economy ministry wanted to publish the names.
In order to deflect criticism away from the party and the Department.
The judge said the court could not draw the conclusion that the Minister had acted in bad faith.
The lawyer acting for the Renewable Heat Association said the judge's decision to be appealed.
The judge said the court has the power to order the names to be published, and that the names should be published by the North of the North.
The judge said the court could not draw the conclusion that the Minister had acted in bad faith.
The judge said the court has the power to order the names to be published, and that the names should be published by the North of the North.
The judge said the court could not draw the conclusion that the Minister had acted in bad faith.
The judge said the court has the power to order the names to be published, and that the names should be published by the North of the North.
The judge said the court could not draw the conclusion that the Minister had acted in bad faith.
The judge said the court has the power to order the names to be published, and that the names should be published by the North of the North.
The judge said the court could not draw the conclusion that the Minister had acted in bad faith.
The judge said the court has the power to order the names to be published, and that the names should be published by the North of the North.
The judge said the court could not draw the conclusion that the Minister had acted in bad faith.
The judge said the court has the power to order the names to be published, and that the names should be published by the North of the North.
The judge said the court could not draw the conclusion that the Minister had acted in bad faith.
The judge said the court has the power to order the names to be published, and that the names should be published by the North of the North.
The judge said the court could not draw the conclusion that the Minister had acted in bad faith.
The judge said the court has the power to order the names to be published, and that the names should be published by the North of the North.
The judge said the court could not draw the conclusion that the Minister had acted in bad faith.
The judge said the court has the power to order the names to be published, and that the names should be published by the North of the North.
The judge said the court could not draw the conclusion that the Minister had acted in bad faith.
The judge said the court has the power to order the names to be published, and that the names should be published by the North of the North.
```
