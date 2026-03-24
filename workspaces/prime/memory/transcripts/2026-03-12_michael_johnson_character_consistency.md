Meeting Title: Call with MJ.m4a

Meeting created at: 12th Mar, 2026 - 3:57 AM

Michael Johnson - 00:01

So originally, when I thought about this, I thought the problem with character consistency isn't a problem in 3D
animation. And the fact that we can only do three to five seconds isn't a problem, it's a benefit. Because all beats
these days are between three and five seconds. Anyways, so originally, what I thought was the biggest problem
was the short videos, which we're talking way back when. Right. Was actually the solution. So the question was,
how do I get the character consistency? My son is taking an Unreal Engine course, and I bought him Meshy. So
what Meshy does is it takes a drawing you have, and it does a 3D and it does like a T pose, and then it goes all
around, does a 360, up, down, bottom, left, right?

Aiko - 00:53

Yeah, I know about.

Michael Johnson - 00:55

Yeah, meshing. It's great. So what I thought was, if we get our avatars, why not do all the same angles, 360 around
them, up, down, low, high, wide, medium, tight, and go all the way around? And what I found interesting enough,
when Phil was working on this last week, which is when that discussion happened, where I sent you what I sent
you, he was doing that already. So I think I was onto the right idea because that's what these other guys were doing
as well. It's simple. It's like good plans are simple and everyone thinks of them because it's the next logical step.
So here's what I thought. I thought the thing that it's missing is expressions of emotion. So what if my character
sheet didn't just have all the poses right? Like running, moving, standing, surfing, whatever the pose is. Right.

Michael Johnson - 01:47

But it also had a database, maybe hooked up through a graphic file with, like, let's call it, I'll say a black background,
but maybe a green would better for cutting. And I also was able to get all the major emotions. Happy, sad, angry,
joyful, all those things. Right? And that expression was on the person's face. So now when I start to create a
generative video, what I really start with is two characters or three or four characters that already have every pose.
I would want them in the database. Now all I have to do is pull the correct pose for the shot that I want, right? It's
all about angles and height and zooming in, zooming out, and dollying and trucking. What if I am able to pull that
as a reference? Or the AI is.

Michael Johnson - 02:41

1/7

Meeting Title: Call with MJ.m4a

Meeting created at: 12th Mar, 2026 - 3:57 AM

The beings are able to use that as a reference point. So now when, like, on your sheet, you say, who's a character?
Well, it's not Just a picture. It's a link to the database where their pose in the 360 is there. So everything they ever
want to do with that character in that generative video is already created. All you're doing now is picking which
pose goes with your video per character. And here's why that way. Because my other concern, and this is where
I'm. I haven't figured it out yet, is that's great. When you're by yourself, you have one character who's sitting at his
desk or he's walking around outside, or he's, you know, doing something that doesn't involve another person.

Michael Johnson - 03:25

But when it started getting weird, when I started thinking about the proportions of the person relative to the
environment and relative to other people, which I think generative AI and what you guys built has already kind of
solved. So that's what I first thought of. It's like, I have a script, right? I do all fill all the things in that you have there,
right? Use it a little bit more descriptive language. Most that stuff is there, right? And then what I'm really doing is
I'm picking a pose in each scene or telling that the. The being to. To reference the database for each of these
poses. And that way everything's kind of already built. And all it's really doing is interpolating the differences
between the poses and the camera angles. That's it.

Michael Johnson - 04:16

And then the hard part, I think, and I don't know, I'm asking is the background, which is originally why I thought if I
green screen them, maybe the secret is using. I started thinking about like a 3D, but I don't think that's right. I think
the way you're doing it's right. I think you do it with. Let the computer do the work. The being do the work of
generating the interpolation between the poses. Give it access to all the poses and the emotions so that all you're
really picking isn't whether or not my character looks right, because it's already there, built into that database.
That's it. That's kind of what I sent over to you.

Aiko - 04:56

Yeah, that's very helpful. And I think that it adds more instead of like it. I think of when we like build these things,
the best method is the method where we need like with the least amount of revision. And so what's going to give it
the least amount of revision is like having an actual realistic 3D modeled like rendering of like realism and giving
them a sense of understanding. Physics is a game changer because they have A huge gap in understanding
physics. I mean, it might even be. It might even make sense to add a knowledge base about physics.

Michael Johnson - 05:36

Dude, that'd be sick. That would be sick. Yeah, that would be sick. That's how they do it in After Effects. So in After
Effects, you have what's called a particle generator. And then a particle generator, you could choose. It's just, it's a
particle emitter. And I go, what would you use that for? Well, fire, smoke, a comet's tail, a magical wand, anything
2/7

Meeting Title: Call with MJ.m4a

Meeting created at: 12th Mar, 2026 - 3:57 AM

that requires a lot of small little dust fragments that you need to kind of like shoot across the screen. And what you
do is you have in like After Effects, the particle generators, you have like velocity, you have gravity, you have how
many is emitting from that part, from that spot. And then you have the keyframe path that you take that emitter
across the room on.

Michael Johnson - 06:24

And then you can actually program each of the individual particles with a shape, with the color and with the
opacity. And you could even upload your own very specific dimensions. Though. The thing is, though, once you
start getting into physics models, right, so there's like two things that used to be the top of computing. They were
video production. And what beat video productions was physics models. So like galaxies being born and nuclear
bombs being exploded, like, those were the ones that required the most data intensive processing. Number two
was video production. Animation. I think, though AI is probably higher than that now, undoubtedly just because of
how many different points of data it's got to interface with. But my concern about using particles and, you know,
I'm probably being silly, like, it's probably.

Michael Johnson - 07:28

There's probably something out there that already does it, you know, it's atmosphere. It's like where I'm standing
now, I'm in my backyard, there's a light on my neighbor's yard. And because it just rained, it's super foggy
everywhere. It looks really cool out here, you know, but like that atmosphere is part of a setting. So I wonder if
somehow those are built in. But the physics is right, though. It's like, how do you get them to walk and not look like
they're bouncing on the moon or something like that? I don't know. Hopefully they're trained that way. That's a good
question, though.

Aiko - 08:00

I think, like, it's a lot of these models have a lot of training on, like, especially from where they started to now on
those things. But I don't think it hurts to look at what's out there to enhance what we already have. And I just like
Looked up like, does After Effects have API and can the infrastructure of our being handle it? And I'm fine. And it's
like, yes, they do.

Michael Johnson - 08:27

But rendering times are tremendous.

Aiko - 08:31

3/7

Meeting Title: Call with MJ.m4a

Meeting created at: 12th Mar, 2026 - 3:57 AM

You might want to find a local solution then. Rendering is contingent on the hardware hosting it. And what sucks
about publicly available tools, which is why I want to find really good local video rendering tools because it's
contingent on our hardware. It's like why it takes so long on the cloud or for CLING or these other providers is
because we're competing with everybody who's awake at that hour who's trying to create media. And so if we are
on our own hardware and we have our own local tools, then we're not competing with anyone. And it's contingent
to our graphics card, our vram.

Michael Johnson - 09:14

Yeah, we could build stuff like that. I've worked in large stations where we use network servers with lots of Gogo to
go and like Z processors, right? Multiple, multiple multi processors one board. And I mean art is very similar to
what you use. And you know, you've done video production, so you're, you know, I'm not telling you anything you
don't know. So like, yeah, we could totally do something like that. But like I just did like an after Effects project and
it was like I wanted to do. It was simple. It was a video analyzation of. It was a video analyzer, audio analyzer,
which is just a spectrum, like audio bump wave, just for, you know, 20 minutes. And I went with VEED IO because
VEED IO produced it like quickly.

Michael Johnson - 10:07

Mine wanted four and a half hours to make it so 30 minute video. So it gets. Rendering gets really tough when you
add physics properties to it, especially with particles and stuff. That's why I think that's why I said, I corrected
myself. I'm like, what you have already looks really good. And I think we just get that character consistency using
the modeling. Once we use the modeling, then we could go ahead and use the beat sheet. And we use the beat.
Once we have that beat sheet. Well, actually your layout first is, I think is what you already have. It's. Everything's
there. It's got to produce a script at some point. That script's got to be followed into beats. Or maybe it's script,
storyboard, then beats probably more accurate. So you can make sure it looks like what it should. Right?

Michael Johnson - 10:55

But it's like once you have that script, you have the storyboard. Once you have the storyboard, you have the model
plugged into different Places. Then you're looking at beats. You're just picking little fine tuned stuff. And I bet you
could probably export something before you even get to all the beat. Fine tuned stuff. And it will look pretty damn
close. It should look pretty close at that point logically to what you're trying to produce. Maybe not perfectly the
way it looks, but like logically it's follows a storyline without that third step. And you're like, yes, that's what
happened in the store. The guy went to the refrigerator, he pulled out a bottle of milk, he opened the bottle of milk,
he poured a bowl of cereal and he ate it.

Michael Johnson - 11:30

4/7

Meeting Title: Call with MJ.m4a

Meeting created at: 12th Mar, 2026 - 3:57 AM

Then you know, maybe whatever it is all the detail after that, but those things have to be there before you get to
that final step of like making it look pretty. Like the basics movements have to be there already. I think maybe. I
don't know, I've never done it before.

Aiko - 11:45

Yeah, this is really helpful. And I found out that After Effects has. You can download it on your hardware and it's
very compatible with our instance of our being. And it could use. We could use After Effects and have it render on
our hardware and it can apply it directly to our video editing pipeline that we're building right now.

Michael Johnson - 12:05

Yeah, it's the best. After Effects is what they use for like Jurassic Park, Star Wars. That's what they use. That's like
the program. Go to video copilot.net It'll give you a really good idea of like the far end of what you can do with it. It's
pretty cool. Yeah, like glow lasers, stop motion, I mean all kinds of crazy stuff you can do. Gears. It also uses
ActionScript which is I think a form of Java. And I think Action Scripts lets you do a lot of mathematical things that
are very cool. You know, you can get into like Gears turning and ratios and things that require only math, which is
good for computers and will increase your running time and looks really smart when you do it on a bigger picture.
Transformers, After Effects, Transformers movies.

Aiko - 13:03

Yeah. And what's cool is like, I don't know if you knew this, but we could like these beings can directly hook up to
Blender. You know Blender?

Michael Johnson - 13:16

Oh yeah.

Aiko - 13:17

It could hook up to blender and create 3D models from scratch as well.

5/7

Meeting Title: Call with MJ.m4a

Meeting created at: 12th Mar, 2026 - 3:57 AM

Michael Johnson - 13:21

Nice. And so have you tried Metahuman?

Aiko - 13:26

I've looked into. I almost used Metahuman for a project before, but I didn't. We didn't end up using it because at the
point I looked into it, we couldn't use it for Kali.

Michael Johnson - 13:36

Right.

Aiko - 13:36

But I mean I, we have, I want to like fill them up with all the tools because why limit. Like we have all these, we have
unlimited resources. Like why not give them everything and play with it and see what it can do? Because like what
makes this game changing is like we're taking all of the best of what's out there and combining it into one
application. So it's like if there's something that we see that it can't do, all we need to do is get API access or get it
locally and like give the being access and we have instant add on features like in minutes.

Michael Johnson - 14:12

So sick. That's so awesome that you guys are working like that. I can't wait to see what this final what we produce
with it. I mean really think about it. Imagine you're like I know you're super creative because I saw your music
videos. Imagine like being able to take your script for whatever AI or not AI, whatever sci fi movie you've been
thinking about making and just dropping it on a timeline, filling out a couple of prompts and producing an entire
movie. It's like sound. And I mean, you know what it does, it frees all the creative people in the world. They're no
longer like, everyone's afraid that AI is going to be restrictive. It's not. It takes the power away from the big movie
studios and gives it to anyone who has an idea and wants to make it happen. That's amazing, dude.

6/7

Meeting Title: Call with MJ.m4a

Meeting created at: 12th Mar, 2026 - 3:57 AM

Michael Johnson - 15:02

That's world changing. Like for real. That would change the whole world.

Aiko - 15:08

Yeah, and we have the vision for it. Because when I brought this project to my team and I was like, I'm gonna do
this, they're like, oh, that's not gonna happen. Then three hours later we have like a V1, and then one hour later we
have V2. And now the team is like saying like, oh, I'm trying this. This isn't working. I'm taking a screenshot and it's
like debugging live. Like Lord no. Looked at the back end of the code and told me all the bugs. I literally take a
screenshot and send it to Sai and she fixes it all. So like, yeah, it's already built. Yeah, we're troubleshooting. Yeah,
we're debugging. Something that would take a regular like dev team a year to do in one life.

Michael Johnson - 15:46

No, what you're doing now has never been done, dude. Never in the history of the world been done. Like for real. If
someone had this power, they bought it and they hid it under a rock. And you know who bought it and hit it under a
rock? The same people who buy ideas for non gas cars and hide them under rocks.

Aiko - 16:08

Oh yeah.

Transcribed by https://fireflies.ai/

7/7

