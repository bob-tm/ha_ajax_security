# Ajax Security Card Example for Home Assistant 

![image](https://github.com/bob-tm/ha_ajax_jeedom/blob/main/ui/card.jpg)

In my example I have 4 different groups.
- Arm/Disarm - global Hub control
- Group - disarm selected zones. In my example it's House, Garage and Yard. (Still can not understand why original APP do not have such button)
- Night mode (not armed on my photo)
- 4 Armed different zones (Red bottom border - Armed)
- Last Ajax message
- Malfunctions message for last Arm Attempt. In my example it's Low Battery and Deactivated wall switch.

My card represent original APP logic as close as possible. 

My integration was build with good UI in mind, so there are state sesnors for 
- hub (sensor.000xxxxx_hub_state)
- Night Mode (sensor.000xxxxx_night_mode_state)
- each group (sensor.00000001_state, sensor.00000002_state, etc)

Values for this sensors can be:
- Disarmed
- Request
- ArmAttempt
- Armed
- ArmedWithErrors

hub_state additionale can be 
- PartiallyArmed

This values used to dispaly different colors and icons for different states. 

There is separate sesnor for SECURITY and ALARAM messages. Everything important will be displayed in this simple card

This is example for Home Group

```yaml
- type: custom:button-card
        entity: sensor.ajax_house_state
        icon: mdi:home
        show_name: false
        state:
          - value: Armed
            color: DarkSlateblue
          - value: ArmedWithErrors
            color: DarkSlateblue
          - value: Request
            color: green
            icon: mdi:power
            styles:
              card:
                - animation: blink 1s ease infinite
          - value: ArmAttempt
            color: orange
            icon: mdi:alert
            styles:
              card:
                - animation: blink 1s ease infinite
          - value: Disarmed
            color: gray
        tap_action:
          action: call-service
          service: switch.toggle
          data:
            entity_id: switch.ajax_house_arm
        hold_action:
          action: call-service
          service: switch.toggle
          data:
            entity_id: switch.ajax_house_force_arm
        styles:
          card:
            - background: none
            - border: 0
            - border-bottom: |
                [[[
                  var x = (entity.state=='Armed') || (entity.state=='ArmedWithErrors');
                  if (x) return '2px solid darkred';
                ]]]
          icon:
            - color: |
                [[[
                  var x = (entity.state=='Armed') || (entity.state=='ArmedWithErrors');
                  if (x) return 'DarkSlateblue'; else return 'gray';
                ]]]
```

# Arming
There are two possible actions fro Hub and Groups ARM:
- tap on icon, ARM. If there will be some errors (open dors, low battery, power failure) - system will not be armed, red icon will blink. 
- hold on icon, Force ARM. System will be ARMED ignoring all errors.

Group ARM/DISARM uses custom service, provided by my integration. 
Change 1,2,4 to you group ID. command can be 'DISARM' or 'ARM', additionaly 'ignore_problems: yes' can be added to Force ARM with malfunctions.

```yaml
- type: custom:button-card
        icon: mdi:home-group-minus
        layout: icon_name
        name: Group
        tap_action:
          action: call-service
          service: ajax_jeedom.arm_disarm
          data:
            entity_id: button.ajax_hub_arm
            command: DISARM
            groups: 1,2,4
```

Only one last message is displayed in UI
- Tap on last message text to see security events history
- Hold on last message text to see malfuntions history 

My card uses 
- [Custom Button Card](https://github.com/custom-cards/button-card) to display different groups states
- [Restriction Card](https://github.com/iantrich/restriction-card) as accidental touch protection
- [Card Mod](https://github.com/thomasloven/lovelace-card-mod) to cahange animation params for Restriction Card

# Examples
There are [Full](https://github.com/bob-tm/ha_ajax_jeedom/blob/main/ui/ajax_example_full.yaml) and [Basic](https://github.com/bob-tm/ha_ajax_jeedom/blob/main/ui/ajax_example_basic.yaml) code examples.

Just add new card, choose manual and copy paste from files above. Then rename you sensors and it should work out of box.

Basic uses only Custom Button Card and can work with visual UI editor in HA. Better start from this one, to config everything as you want. 

Full adds protection overlay using Restriction Card. You can limit by user, add pins, etc

enjoy!
