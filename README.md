# Flappy Bird Pose Camera

A clone of the popular app *Flappy Bird*, using Pygame.

This code is forked from https://github.com/TimoWilken/flappy-bird-pygame

# Magic behind the scenes

```python
        if cam.isOpened():
            ret, image = cam.read()
            image = cv2.flip(image, 1)
            image = cv2.resize(image, (WIN_WIDTH, WIN_HEIGHT))

            poses = posecamera.estimate(image)
            for pose in poses:
                # pose.draw(image)
                nose = pose.keypoints[0]
                bird.x = nose[0]
                bird.y = nose[1]
```

